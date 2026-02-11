import time
import asyncio
import re
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

def get_429_retry_delay(error) -> int:
    """Calculate delay for 429 errors."""
    delay = 15  # default delay
    for d in error.details["error"].get('details', []): 
        if '@type' in d and d['@type'] == 'type.googleapis.com/google.rpc.RetryInfo':
            retry_delay = d.get('retryDelay', '15s')
            delay_match = re.match(r'(\d+)(\.\d+)?s', retry_delay)
            if delay_match:
                delay = int(float(delay_match.group(1) + (delay_match.group(2) or '')))
    # add random jitter of up to 5 seconds
    jitter = random.randint(1, 5)
    return delay + jitter

class SubAgentGoogle:
    """Sub-Agent using Google ADK LlmAgent for MCP tool integration."""
    
    def __init__(self, name, model, token_tracker, system_instruction, mcp_toolset: McpToolset = None, planner=None, rate_limiter=None):
        self.agent_name = name
        self.token_tracker = token_tracker
        self.model = model
        self.system_instruction = system_instruction
        self.debug = False
        self.progress_indication = True

        # Create LlmAgent with ADK
        agent_args = {}
        if mcp_toolset:
            agent_args['tools'] =  [mcp_toolset]
        if planner:
            agent_args['planner'] = planner
        if rate_limiter:
            agent_args['before_model_callback'] = rate_limiter.before_call
            agent_args['after_model_callback'] = rate_limiter.after_call
            
        self.agent = LlmAgent(
            model=model,
            name=self.agent_name,
            instruction=system_instruction,
            **agent_args
        )
                    
        # Create runner for execution with session service
        self.session_service = InMemorySessionService()
        self.agent_runner = Runner(
            agent=self.agent,
            app_name=self.agent_name,
            session_service=self.session_service
        )
    
    def set_debug(self, debug: bool):
        """Enable or disable debug printing."""
        self.debug = debug
    def set_progress_indication(self, progress_indication: bool):
        """Enable or disable progress indication."""
        self.progress_indication = progress_indication

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

    def _function_response_result(self, result):
        """Extract success status from function response."""
        function_response = result.get('structuredContent', {})
        if 'success' in function_response:
            is_success = function_response['success']
        else:
            is_success = not result.get('isError', False)
        return is_success        

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


    async def _async_query(self, query=None, parts=None, stopword=None, n_iterations=20) -> Dict[str, Any]:
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
                message += f"\n\n## {title}\n{content}"
        
        # Use a consistent session ID for this query
        session_id = f"{self.agent_name}_{int(time.time())}"
        user_id = f"{self.agent_name}_user"
        
        final_text = ""
        token_usage = None
        function_call_count = 0
        conversation_history = []
        
        if self.debug:
            print(f"📝 User message: {message[:200]}{'...' if len(message) > 200 else ''}")
        if self.progress_indication:
            print(f"⏳ Agent {self.agent_name} processing", end="", flush=True)

        # Create session
        try:
            session = await self.session_service.create_session(
                app_name=self.agent_name,
                user_id=user_id,
                session_id=session_id
            )
        except Exception as session_error:
            if self.debug:
                print(f"⚠️  Session creation failed, continuing anyway: {session_error}")
        
        stopword_received = False
        abnormal_termination = False
        n_iteration = 0
        message=types.Content(role='user', parts=[types.Part(text=message)])
        query_start_time = asyncio.get_event_loop().time()
        try:
            while n_iteration < n_iterations:
                # Run agent with streaming events
                start_time = asyncio.get_event_loop().time()
                async for event in self.agent_runner.run_async(
                    user_id=user_id,
                    session_id=session_id, 
                    new_message=message
                ):
                    # Handle event content (text and function calls)
                    agent_text = ""
                    conversation_history.append(event)
                    if self.progress_indication:
                        print(".", end="", flush=True)
                    if hasattr(event, 'content') and hasattr(event.content, 'parts') and event.content.parts:
                        for part in event.content.parts:
                            # Handle text response
                            if hasattr(part, 'text') and part.text:
                                agent_text += part.text
                            
                            # Handle function calls
                            if hasattr(part, 'function_call') and part.function_call:
                                function_call_count += 1
                                if self.debug:
                                    self._function_call_debug_print(part.function_call)
                                    
                            # Handle function responses
                            if hasattr(part, 'function_response') and part.function_response:
                                if self.debug:
                                    self._function_response_debug_print(part.function_response.response)
                                function_name = part.function_response.name if part.function_response.name else "unknown"
                                is_success = self._function_response_result(part.function_response.response)
                                # Record function call stats
                                self.token_tracker.record_function_call(self.model, function_name, is_success)

                    if self.debug and agent_text:
                        print(f"🤖📢 {agent_text}")
                    final_text = agent_text

                    if stopword and stopword in agent_text:
                        stopword_received = True
                        if self.debug:
                            print("🚦 Stopword received.")

                    # Extract token usage if available
                    if hasattr(event, 'usage_metadata') and event.usage_metadata:
                        token_usage = event.usage_metadata     
                        self.token_tracker.record(self.model, token_usage, 0)     
                        if self.debug:
                            elapsed_time = asyncio.get_event_loop().time() - query_start_time
                            self.token_tracker.print_call_info(token_usage, elapsed_time)     
                    # Check if this is the final response
                    is_final = hasattr(event, 'is_final_response') and event.is_final_response()
                    if is_final and self.debug:
                        print("✅ Final response received")
                    # Don't break immediately - let the loop finish processing any remaining content
                    # The while loop will exit naturally when no more events are available

                end_time = asyncio.get_event_loop().time()
                generation_time = end_time - start_time
                self.token_tracker.record_time(self.model, generation_time)

                if not stopword:
                    break  # No stopword specified, exit after first run
                elif stopword_received:
                    break  # Stopword received, exit loop
                else:
                    print("🛑 No stopword received, continuing.")
                    n_iteration += 1
                    message = types.Content(role='user', parts=[types.Part(text="You did not finish your tasks. Please continue and complete them. When done, end with '###STOPWORD###'.")])
        except (asyncio.CancelledError, KeyboardInterrupt):
            print("\n🛑 Interrupted by user (Ctrl+C). Exiting gracefully...")
            abnormal_termination = True
        
        if abnormal_termination:
            summary = self.token_tracker.summary()
            print(f"📊 Usage summary for {self.model} before termination:")
            for line in summary:
                print(line)

        if self.progress_indication:
            print(" Done.")

        # Return in same format as original SubAgentBase
        return {
            "text": final_text,
            "full": conversation_history,
            "usage": token_usage,
            "response_time": generation_time
        }

    async def query(self, query=None, parts=None, stopword=None, n_iterations=20) -> Dict[str, Any]:
        """Async query interface. Caller must manage event loop."""
        max_retries = 10
        
        for attempt in range(max_retries):
            try:
                return await self._async_query(query=query, parts=parts, stopword=stopword, n_iterations=n_iterations)
                    
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
            except errors.ClientError as e:
                if e.code == 429:
                    delay = get_429_retry_delay(e)
                else:
                    delay = 5  # default delay for other client errors
                print(f"⚠️  Client error: {e.code} - {e.message}")
                print(f"🔄 Retrying in {delay}s...")
                await asyncio.sleep(delay)  # Use async sleep
            except Exception as e:
                # For other exceptions, don't retry
                print(f"❌ Non-retryable error: {e}")
                raise

    def query_sync(self, query=None, parts=None, stopword=None, n_iterations=20) -> Dict[str, Any]:
        """Sync wrapper - creates new event loop (use sparingly)."""
        return asyncio.run(self.query(query=query, parts=parts, stopword=stopword, n_iterations=n_iterations))
