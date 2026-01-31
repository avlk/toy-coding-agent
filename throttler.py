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
from google.genai.local_tokenizer import LocalTokenizer

class ElegantThrottler:
    def __init__(self, rpm: int, tpm: int, model: str):
        # Local tokenizer (no network calls)
        if model.startswith("gemini-3"):
            model="gemini-2.5-flash" # Use 2.5 tokenizer for 3.x models for now
        self.tokenizer = LocalTokenizer(model_name=model)
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

    def _predict_input_cost(self, llm_request) -> int:
        count = 0
        
        # 1. Robust System Instruction Counting
        if hasattr(llm_request, 'config') and llm_request.config.system_instruction:
            si = llm_request.config.system_instruction
            
            # Case A: It's a raw string
            if isinstance(si, str):
                count += self.tokenizer.count_tokens(si).total_tokens
            
            # Case B: It's a Content object with .parts
            elif hasattr(si, 'parts'):
                for part in si.parts:
                    if hasattr(part, 'text') and part.text:
                        count += self.tokenizer.count_tokens(part.text).total_tokens
        
        # 2. Robust Content (History) Counting
        if hasattr(llm_request, 'contents'):
            for content in llm_request.contents:
                # Some contents might also just be strings in certain ADK versions
                if isinstance(content, str):
                    count += self.tokenizer.count_tokens(content).total_tokens
                    continue
                
                # Otherwise, iterate through parts
                if hasattr(content, 'parts'):
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            count += self.tokenizer.count_tokens(part.text).total_tokens
                        elif hasattr(part, 'inline_data') or hasattr(part, 'file_data'):
                            count += 258 # Standard Gemini cost for media
        
        # 3. Add safety buffer for tool definitions/JSON overhead
        # (Tier 1 is very sensitive, so 15% is a safe bet)
        return int(count * 1.15) + 150

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