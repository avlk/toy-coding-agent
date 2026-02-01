# Throttling logic to limit requests per minute (RPM) for LLM agents.
# --- Usage ---

# Create an agent with a custom 250 RPM. 500k TPM limit
# throttler = get_throttler(rpm=250, tpm=500_000, model="gemini-2.5-flash")
# agent_a = LlmAgent(
#     model="gemini-2.5-flash",
#     before_model_callback=throttler.before_call,
#     after_model_callback=throttler.after_call
# )

import asyncio
from throttled import RateLimiterType, rate_limiter
from throttled.asyncio import Throttled
from litellm import token_counter

class ElegantThrottler:
    def __init__(self, rpm: int, tpm: int, model: str):
        self.model_name = model
        self.tpm = tpm
        self.debug = False

        # RPM Limit: Every call has a cost of 1
        self.rpm_limiter = Throttled(
            using="token_bucket",
            quota=rate_limiter.per_min(rpm)
        )
        
        # TPM Limit: Every call has a cost of N (tokens)
        self.tpm_limiter = Throttled(
            using="token_bucket",
            quota=rate_limiter.per_min(tpm)
        )

        self.token_debt = 0
        self.last_prediction = 0
        self.lock = asyncio.Lock()

    def _predict_input_cost(self, request) -> int:
        """Deep inspection of ADK LlmRequest for accurate counting."""
        messages = []
        
        # 1. System Instruction
        si = getattr(request.config, 'system_instruction', "")
        if si:
            content = si if isinstance(si, str) else " ".join(p.text for p in getattr(si, 'parts', []) if p.text)
            messages.append({"role": "system", "content": content})
            
        # 2. History (Text + Tool Results + Function Calls)
        for content in getattr(request, 'contents', []):
            role = "assistant" if content.role == "model" else "user"
            combined_text = []
            
            if hasattr(content, 'parts'):
                for part in content.parts:
                    if part.text:
                        combined_text.append(part.text)
                    # TOOL RESULTS (This is usually where the hidden bulk lives)
                    elif hasattr(part, 'function_response') and part.function_response:
                        # Convert the tool output dict to string to count it
                        combined_text.append(str(part.function_response.response))
                    # TOOL CALLS (The model's intent to use a tool)
                    elif hasattr(part, 'function_call') and part.function_call:
                        combined_text.append(str(part.function_call.args))
            
            messages.append({"role": role, "content": " ".join(combined_text)})

        # 3. TOOL DEFINITIONS (The biggest hidden cost in agents)
        # Each tool schema is roughly 200-1000 tokens depending on complexity
        tool_overhead = 0
        if hasattr(request, 'tools') and request.tools:
            # We stringify the first tool to estimate average schema size
            sample_tool = str(request.tools[0])
            avg_tool_size = token_counter(model="gpt-4", text=sample_tool)
            tool_overhead = avg_tool_size * len(request.tools)

        try:
            # Use gpt-4 as a proxy for Gemini 3 density if it's underestimating
            base_count = token_counter(model="gpt-4", messages=messages)
            return base_count + tool_overhead + 200 # Constant overhead buffer
        except Exception:
            return 5000 # Panic fallback


    async def _get_available_capacity(self) -> int:
        """Uses peek() to estimate how many tokens are currently in the bucket."""
        state = await self.tpm_limiter.peek(key="global_gate")
        return (state.remaining / state.limit)

    async def _draw_bar(self):
        """Draws the bar based on actual bucket state via peek()."""
        current_capacity = await self._get_available_capacity()
        
        bar_length = 20
        filled_length = int(bar_length * current_capacity)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f"🛑 [TPM level] |{bar}|")
        
    async def before_call(self, callback_context, llm_request):
        async with self.lock:
            # 1. Predict what this call will cost
            self.last_prediction = self._predict_input_cost(llm_request)
            
            # 2. Add any debt from the PREVIOUS call to THIS call's cost
            current_cost = self.last_prediction + max(0, self.token_debt)
            
            if self.debug:
                await self._draw_bar()
                print(f"⚖️  [TPM GATE] Debt: +{self.token_debt} tokens")
                print(f"🚀 [NEXT CALL] Est. Cost: {self.last_prediction} tokens")

            # 3. Apply the throttle
            await self.rpm_limiter.limit(key="global_gate", cost=1, timeout=120)
            await self.tpm_limiter.limit(key="global_gate", cost=current_cost, timeout=120)
            
            # Reset debt now that we've "paid" it by waiting
            self.token_debt = 0
            return None

    async def after_call(self, callback_context, llm_response):
        async with self.lock:
            if hasattr(llm_response, 'usage_metadata'):
                meta = llm_response.usage_metadata
                
                # Total tokens = Input + Output + Thinking
                actual_total = meta.total_token_count
                
                # If actual > prediction, we have a debt for the next call
                if actual_total > self.last_prediction:
                    self.token_debt = actual_total - self.last_prediction
                    if self.debug:
                        print(f"📉 [SETTLEMENT] Predicted: {self.last_prediction} | Actual: {actual_total}")
                        print(f"⚠️  [DEBT] +{self.token_debt} tokens incurred (Thinking/Output).")
                else:
                    # If the model was surprisingly brief, we have no debt
                    self.token_debt = 0
            return None

def get_throttler(rpm: int, tpm: int, model: str) -> ElegantThrottler:
    """Factory to create the throttler instance."""
    return ElegantThrottler(rpm, tpm, model=model)