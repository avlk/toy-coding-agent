from ratelimit import limits, sleep_and_retry

# Throttling logic to limit requests per minute (RPM) for LLM agents.
# --- Usage ---

# Create an agent with a custom 50 RPM limit
# agent_a = LlmAgent(
#     model="gemini-1.5-pro",
#     before_model_callback=get_throttler(50)
# )


class Throttler:
    def __init__(self, rpm: int):
        self.rpm = rpm
        
        # This function keeps track of the "state" for this specific instance
        @sleep_and_retry
        @limits(calls=self.rpm, period=60)
        def _limit_logic(request):
            return request
        
        self._limit_logic = _limit_logic

    def get_callback(self):
        """
        Returns a lambda that matches the ADK signature.
        We use **kwargs to catch 'callback_context' and 'request' 
        regardless of how the ADK decides to pass them.
        """
        return lambda **kwargs: self._limit_logic(kwargs.get('request'))

def get_throttler(rpm: int):
    """Factory function to return a fresh throttling lambda."""
    return Throttler(rpm).get_callback()
