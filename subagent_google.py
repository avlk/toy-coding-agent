import time
import asyncio
from google import genai
from google.genai import errors, types
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
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


class SubAgentGoogle:
    """Sub-Agent using Google ADK LlmAgent for MCP tool integration."""
    
    def __init__(self, llm, model, token_tracker, base_config: genai.types.GenerateContentConfig, system_instruction, mcp_toolset: McpToolset = None):
        self.llm = llm  # Keep for compatibility but won't use directly
        self.token_tracker = token_tracker
        self.model = model
        self.system_instruction = system_instruction
        
        # Build tools list for LlmAgent
        tools = []
        if mcp_toolset:
            tools = [mcp_toolset]
        
        # Create LlmAgent with ADK
        try:
            print(f"🔍 Creating LlmAgent with model: {model}")
            
            # Basic agent creation - start simple
            self.agent = LlmAgent(
                model=model,
                name='subagent',
                instruction=system_instruction
            )
            
            # Add tools separately if available
            if tools:
                try:
                    # Check if we can set tools on the agent
                    if hasattr(self.agent, 'tools'):
                        self.agent.tools = tools
                        print(f"✅ Added {len(tools)} MCP toolsets to agent")
                    else:
                        print(f"⚠️  Agent doesn't support tools attribute, trying constructor again")
                        self.agent = LlmAgent(
                            model=model,
                            name='subagent', 
                            instruction=system_instruction,
                            tools=tools
                        )
                        print(f"✅ Created LlmAgent with {len(tools)} MCP toolsets")
                except Exception as tool_error:
                    print(f"⚠️  Failed to add tools: {tool_error}")
                    print(f"⚠️  Continuing with agent without tools")
            
            # Create runner for execution with session service
            self.session_service = InMemorySessionService()
            self.agent_runner = Runner(
                agent=self.agent,
                app_name='subagent',
                session_service=self.session_service
            )
            
            print(f"✅ Created LlmAgent successfully")
            
        except Exception as e:
            print(f"❌ Failed to create LlmAgent: {e}")
            import traceback
            traceback.print_exc()
            # Fallback - create empty agent
            self.agent = None
            self.agent_runner = None
            self.session_service = None
    
    def _function_call_debug_print(self, function_call):
        """Debug print for function calls - mimicking original interface."""
        if hasattr(function_call, 'name') and hasattr(function_call, 'args'):
            params_str = ", ".join(f"{k}={format_param_value(v)}" for k, v in function_call.args.items())
            print(f"🤖➡️ Function call: {function_call.name}({params_str})", flush=True)
            for k, v in function_call.args.items():
                if isinstance(v, list):
                    print(f"    {k}:")
                    for line in v:
                        print(f"        '{line}'")
        else:
            print(f"🤖➡️ Function call: {function_call}", flush=True)

    def _function_response_debug_print(self, result):
        """Debug print for function responses - mimicking original interface."""
        if isinstance(result, dict):
            # Check for 'success' key first, otherwise fall back to isError
            if 'success' in result:
                is_success = result['success']
            else:
                is_success = not result.get('isError', False)
            
            if is_success:
                response = "✅ Success"
            else:
                response = "❗Error"
                if 'error' in result:
                    response += f": {result['error']}"
        else:
            response = f"✅ Response: {result}"
        print(f"🤖↩️ Function response: {response}", flush=True)

    async def _async_query(self, query=None, parts=None, debug=False) -> Dict[str, Any]:
        """Async implementation using LlmAgent."""
        if not self.agent or not self.agent_runner:
            raise RuntimeError("LlmAgent not properly initialized")
        
        # Build message from query and parts
        if query:
            message = query
        else:
            message = ""
        
        if parts:
            for title, content in parts:
                message += f"\n\n# {title}\n{content}"
        
        start_time = time.monotonic()
        
        # Use a consistent session ID for this query
        session_id = f"subagent_{int(time.time())}"
        user_id = "subagent_user"
        
        final_text = ""
        token_usage = None
        function_call_count = 0
        
        try:
            if debug:
                print(f"\n🔄 --- LlmAgent Query ---\n", flush=True)
                print(f"📝 User message: {message[:200]}{'...' if len(message) > 200 else ''}")
            
            # Create session if needed
            try:
                session = await self.session_service.create_session(
                    app_name='subagent',
                    user_id=user_id,
                    session_id=session_id
                )
            except Exception as session_error:
                if debug:
                    print(f"⚠️  Session creation failed, continuing anyway: {session_error}")
            
            # Run agent with streaming events
            async for event in self.agent_runner.run_async(
                user_id=user_id,
                session_id=session_id, 
                new_message=types.Content(role='user', parts=[types.Part(text=message)])
            ):
                # Handle event content (text and function calls)
                if hasattr(event, 'content') and hasattr(event.content, 'parts') and event.content.parts:
                    for part in event.content.parts:
                        # Handle text response
                        if hasattr(part, 'text') and part.text:
                            agent_text = part.text
                            if debug:
                                print(f"🤖📢 {agent_text}")
                            final_text += agent_text
                        
                        # Handle function calls
                        if hasattr(part, 'function_call') and part.function_call:
                            function_call_count += 1
                            if debug:
                                self._function_call_debug_print(part.function_call)
                                
                        # Handle function responses
                        if hasattr(part, 'function_response') and part.function_response:
                            if debug:
                                self._function_response_debug_print(part.function_response.response)
                
                # Extract token usage if available
                if hasattr(event, 'usage_metadata') and event.usage_metadata:
                    token_usage = event.usage_metadata
                
                # Check if this is the final response - but process content first before breaking
                is_final = hasattr(event, 'is_final_response') and event.is_final_response()
                if is_final:
                    if debug:
                        print("✅ Final response received")
                    # Don't break immediately - let the loop finish processing any remaining content
                    # The while loop will exit naturally when no more events are available
        
        except Exception as e:
            print(f"❌ Error in LlmAgent query: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        end_time = time.monotonic()
        generation_time = end_time - start_time
        
        # Track tokens if available
        if token_usage:
            self.token_tracker.print_call_info(token_usage, generation_time)
            self.token_tracker.record(self.model, token_usage, generation_time)
        elif debug:
            print(f"⚠️  No token usage information available from LlmAgent")
        
        # Return in same format as original SubAgentBase
        return {
            "text": final_text,
            "full": None,  # LlmAgent manages conversation internally
            "usage": token_usage,
            "response_time": generation_time
        }

    async def query(self, query=None, parts=None, debug=False) -> Dict[str, Any]:
        """Async query interface. Caller must manage event loop."""
        max_retries = 10
        
        for attempt in range(max_retries):
            try:
                return await self._async_query(query=query, parts=parts, debug=debug)
                    
            except errors.ServerError as e:
                if attempt < max_retries - 1:
                    # 15 seconds for 503, 5 seconds for other 5xx errors
                    delay = 15 if e.code == 503 else 5
                    print(f"⚠️  Server error: {e}")
                    print(f"🔄 Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)  # Use async sleep
                else:
                    print(f"❌ Server error after {max_retries} retries: {e}")
                    raise
            except Exception as e:
                # For other exceptions, don't retry
                print(f"❌ Non-retryable error: {e}")
                raise

    def query_sync(self, query=None, parts=None, debug=False) -> Dict[str, Any]:
        """Sync wrapper - creates new event loop (use sparingly)."""
        return asyncio.run(self.query(query=query, parts=parts, debug=debug))