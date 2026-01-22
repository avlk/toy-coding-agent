import time
import asyncio
from google import genai
from google.genai import errors, types
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from patch import patch_code, is_unified_diff
from sandbox_execution import execute_sandboxed
from token_tracker import TokenUsageTracker
from utils import *
from typing import Dict, List, Optional, Union, Tuple, Any


def format_param_value(value):
    """Format parameter values, showing 'N lines' for lists or multiline strings."""
    if isinstance(value, list):
        return f"[{len(value)} lines]"
    elif isinstance(value, str) and '\n' in value:
        line_count = value.count('\n') + 1
        return f"<{line_count} lines>"
    elif isinstance(value, str) and len(value) > 100:
        return f"{value[:100]}..."
    else:
        return str(value)


class SubAgentBase:
    # Sub-Agent performing specific tasks on a project (like: coding, fixing syntax errors, reviewing)
    
    def __init__(self, llm, model, token_tracker, base_config: genai.types.GenerateContentConfig, system_instruction, mcp_toolset: McpToolset = None, allowed_mcp_tools: List[str] | None = None):
        self.llm = llm
        self.token_tracker = token_tracker
        self.config = base_config
        self.model = model
        self.mcp_toolset = mcp_toolset  # Store for function call execution
        self.mcp_tool_map = {}  # Map of tool names to MCPTool objects
        
        # Create persistent event loop for async operations
        try:
            self.loop = asyncio.get_event_loop()
            if self.loop.is_closed():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        if self.config.tools is None:
            self.config.tools = []

        if self.model.startswith("gemini-3"):
            self.config.temperature = 1.0 # For Gemini 3 it is important not to alter the default temperature

        self.config.system_instruction = system_instruction

        if mcp_toolset:
            # Convert McpToolset to function declarations for streaming API
            function_declarations, self.mcp_tool_map = self.mcp_toolset_to_function_declarations(mcp_toolset, allowed_mcp_tools)
            if function_declarations:
                self.config.tools.append(genai.types.Tool(function_declarations=function_declarations))
                
                if self.config.tool_config is None:
                    self.config.tool_config = genai.types.ToolConfig()
                    
                self.config.tool_config.function_calling_config = genai.types.FunctionCallingConfig(mode='AUTO')
            else:
                print("⚠️  No function declarations found from MCP toolset")
    
    def _function_call_debug_print(self, function_call):
        params_str = ", ".join(f"{k}={format_param_value(v)}" for k, v in function_call.args.items())
        print(f"🤖➡️ Function call: {function_call.name}({params_str})", flush=True)
        for k, v in function_call.args.items():
            if isinstance(v, list):
                print(f"    {k}:")
                for line in v:
                    print(f"        '{line}'")

    def _function_response_debug_print(self, result):
        # Check for 'success' key first, otherwise fall back to isError
        function_response = result.get('structuredContent', {})
        if 'success' in function_response:
            is_success = function_response['success']
        else:
            is_success = not result.get('isError', False)
        
        if is_success:
            response = "✅ Success"
        else:
            response = "❗Error"
            if 'error' in function_response:
                response += f": {function_response['error']}"
        print(f"🤖↩️ Function response: {response}", flush=True)                    
        # print(f"Full response: {json.dumps(result)[:500]}", flush=True)


    def _query_attempt(self, query=None, parts=None, debug=False) -> Dict[str, Any]:
        # mark start time
        start_time = time.monotonic()

        request_parts = []
        if query:
            request_parts.append({"text": query})
        if parts:
            # Build parts as proper content structure (not concatenated strings)
            for title, content in parts:
                request_parts.append({"text": f"\n\n# {title}\n{content}"})
        
        conversation_history = [{"role": "user", "parts": request_parts}]
        
        # Function calling loop
        max_rounds = 50
        token_usage = None
        final_text = ""

        for round_num in range(max_rounds):
            if debug:
                print(f"\n🔄 --- Subagent Round {round_num + 1} ---\n", flush=True)
            # Use streaming API
            stream = self.llm.models.generate_content_stream(
                model=self.model, contents=conversation_history, config=self.config
            )
            
            # Process streaming events (synchronously - the stream is a regular generator)
            text_chunks = []
            function_calls = []
            for chunk in stream:
                # print(chunk, flush=True)  # For debugging purposes
                # Process text parts
                if hasattr(chunk, 'text') and chunk.text:
                    text_chunks.append(chunk.text)
                
                # Collect function calls
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        content = getattr(candidate, 'content', None)
                        if not content:
                            continue
                        # Check for function calls in parts
                        parts_list = getattr(content, 'parts', None)
                        if not parts_list:
                            continue
                        for part in parts_list:
                            function_call = getattr(part, 'function_call', None)
                            if function_call:
                                function_calls.append(function_call)
                # Track usage metadata
                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    token_usage = chunk.usage_metadata

            agent_text = ''.join(text_chunks)
            if debug:
                print(f"🤖📢 {agent_text}")

            # Add model response with function calls to history
            model_parts = []
            if text_chunks:
                model_parts.append({"text": agent_text})
            for fc in function_calls:
                model_parts.append({"function_call": fc})
            conversation_history.append({"role": "model", "parts": model_parts})

            # If no function calls, we're done
            if not agent_text and not function_calls:
                print(f" ✅ Model is done processing.")
                final_text = agent_text
                break

            if not function_calls:
                continue  # No function calls to process

            # Execute function calls using MCP tools
            if function_calls and not self.mcp_tool_map:
                print("⚠️  Function calls requested but no MCP tools available")
                break

            # Execute function calls and add responses
            function_response_parts = []
            for fc in function_calls:
                try:
                    # Get the MCPTool object for this function
                    if fc.name not in self.mcp_tool_map:
                        raise ValueError(f"Tool {fc.name} not found in tool map")
                                        
                    # Execute the tool directly with keyword arguments using persistent event loop
                    # MCPTool.run_async expects args and tool_context as keyword args
                    mcp_tool = self.mcp_tool_map[fc.name]
                    result = self.loop.run_until_complete(
                        mcp_tool.run_async(args=dict(fc.args), tool_context=None)
                    )

                    if debug:
                        self._function_call_debug_print(fc)

                    # Format response
                    function_response_parts.append({
                        "function_response": {
                            "name": fc.name,
                            "response": {"result": result}
                        }
                    })
                    if debug:
                        self._function_response_debug_print(result)
                except Exception as e:
                    function_response_parts.append({
                        "function_response": {
                            "name": fc.name,
                            "response": {"error": str(e)}
                        }
                    })
                    if debug:
                        print(f"🤖↩️ Function response: ❗Error: {e}", flush=True)
            
            conversation_history.append({"role": "user", "parts": function_response_parts})
        
        if max_rounds == round_num + 1:
            print(f"⚠️  Max function call rounds ({max_rounds}) reached, stopped.")

        end_time = time.monotonic()
        generation_time = end_time - start_time
        if token_usage:
            self.token_tracker.print_call_info(token_usage, generation_time)
            self.token_tracker.record(self.model, token_usage, generation_time)
        return {"text": final_text, "full": conversation_history, "usage": token_usage, "response_time": generation_time}
    

    def query(self, query=None, parts=None, debug=False) -> Dict[str, Any]:
        max_retries = 10
        
        for attempt in range(max_retries):
            try:
                return self._query_attempt(query=query, parts=parts, debug=debug)
            except errors.ServerError as e:
                if attempt < max_retries - 1:
                    # 15 seconds for 503, 5 seconds for other 5xx errors
                    delay = 15 if e.code == 503 else 5
                    print(f"⚠️  Server error: {e}")
                    print(f"🔄 Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    print(f"❌ Server error after {max_retries} retries: {e}")
                    raise

    def mcp_toolset_to_function_declarations(self, mcp_toolset: McpToolset, allowed_mcp_tools: list[str] = None) -> tuple[list, dict]:
        """Convert McpToolset to function declarations for use with streaming API.
        
        This extracts the tool definitions from McpToolset and converts them to
        the format expected by the streaming API (generate_content_stream).
        
        Returns:
            tuple: (function_declarations list, tool_map dict mapping tool names to MCPTool objects)
        """
        # Get or create event loop for async operations
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Get tools with retries
        tools = None
        # print(f"🔍 Attempting to connect to MCP server and get tools...")
        try:
            tools = loop.run_until_complete(mcp_toolset.get_tools(readonly_context=None))
        except Exception as e:
            print(f"❌ Failed to get MCP tools from server:")
            print(f"   Last error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return [], {}
        
        if not tools:
            print("❌ No tools received from MCP server")
            return [], {}
        else:
            print(f"✅ MCP server announces {len(tools)} tools")
        
        # print(f"🔍 Examining tool structure...")
        function_declarations = []
        tool_map = {}  # Map tool names to MCPTool objects for execution
        
        for i, tool in enumerate(tools):
            # Check if tool is allowed
            if allowed_mcp_tools:
                if tool.name not in allowed_mcp_tools:
                    continue
            # MCPTool has raw_mcp_tool which contains the actual MCP tool
            if not hasattr(tool, 'raw_mcp_tool'):
                continue
            raw_tool = tool.raw_mcp_tool
            
            # Check if raw_tool has inputSchema
            if hasattr(raw_tool, 'inputSchema'):
                # Build function declaration from MCP tool
                func_decl = genai.types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description if hasattr(tool, 'description') else "",
                    parameters=raw_tool.inputSchema
                )
                function_declarations.append(func_decl)
                tool_map[tool.name] = tool  # Store the MCPTool object for later execution

        # Print what functions were added
        if function_declarations:
            func_names = [fd.name for fd in function_declarations]
            print(f"✅ Converted {len(function_declarations)} MCP tools to function declarations: {', '.join(func_names)}")

        return function_declarations, tool_map
