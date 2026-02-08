"""
Token usage tracking for LLM API calls.

This module provides the TokenUsageTracker class for tracking and reporting
token usage statistics across multiple LLM models.
"""

class UsageStats:
    """A simple class to hold usage statistics for an LLM call."""

    class EMPTY_STATS:
        """"An empty statistics object."""
        total_token_count = 0
        cached_content_token_count = 0
        candidates_token_count = 0
        prompt_token_count = 0
        thoughts_token_count = 0
        tool_use_prompt_token_count = 0

    def __init__(self, metadata = EMPTY_STATS):
        self.total_token_count = metadata.total_token_count or 0
        self.cached_content_token_count = metadata.cached_content_token_count or 0
        self.candidates_token_count = metadata.candidates_token_count or 0
        self.prompt_token_count = metadata.prompt_token_count or 0
        self.thoughts_token_count = metadata.thoughts_token_count or 0
        self.tool_use_prompt_token_count = metadata.tool_use_prompt_token_count or 0
        self.llm_run_count = 1 if metadata != self.EMPTY_STATS else 0
        self.function_calls = {}
    
    def __add__(self, other: 'UsageStats') -> 'UsageStats':
        """Add another UsageStats object's values to this one."""
        self.total_token_count += other.total_token_count
        self.cached_content_token_count += other.cached_content_token_count
        self.candidates_token_count += other.candidates_token_count
        self.prompt_token_count += other.prompt_token_count
        self.thoughts_token_count += other.thoughts_token_count
        self.tool_use_prompt_token_count += other.tool_use_prompt_token_count
        self.llm_run_count += other.llm_run_count
        # Merge function call statistics. For every function called, sum the counts.
        for func_name, call_info in other.function_calls.items():
            if func_name not in self.function_calls:
                self.function_calls[func_name] = {'count': 0, 'success': 0, 'failure': 0}
            self.function_calls[func_name]['count'] += call_info['count']
            self.function_calls[func_name]['success'] += call_info['success']
            self.function_calls[func_name]['failure'] += call_info['failure']
        return self

    def billable_tokens(self) -> dict[str, int]:
        """
        Get billable token counts from a statistics item.
        
        Args:
            stat_item: A statistics dictionary for a model

        Returns:
            Dictionary with billable token counts
        """     
        input = self.prompt_token_count + self.tool_use_prompt_token_count
        output =  self.candidates_token_count + self.thoughts_token_count
        cached = self.cached_content_token_count
        input -= cached
        return {
            'cached': cached,
            'input': input,
            'output': output,
        }

class TokenUsageTracker:
    """Tracks token usage statistics across multiple LLM models."""

    PRICING = {
        # Pricing data (per 1M tokens)
        'gemini-3-pro-preview': {
            'input': 2.0,
            'output': 12.0,
            'cached': 0.2
        },
        'gemini-3-flash-preview': {
            'input': 0.5,
            'output': 3.0,
            'cached': 0.05
        },
        'gemini-2.5-pro': {
            'input': 1.25,
            'output': 10.0,
            'cached': 0.125
        },
        'gemini-2.5-flash': {
            'input': 0.3,
            'output': 2.5,
            'cached': 0.03
        },
        'gemini-2.5-flash-lite': {
            'input': 0.1,
            'output': 0.4,
            'cached': 0.01
        },
    }

    def __init__(self):
        """Initialize an empty statistics dictionary."""
        self.stats = {}
        self.time = {}
        self.call_history = []

    def record_usage(self, model_name: str, metadata):
        """
        Record token usage for a model.
        
        Args:
            model_name: Name of the LLM model
            metadata: Usage metadata object from the LLM response
            response_time: Time taken for the LLM call in seconds
        """
        # Initialize stats for new models
        if model_name not in self.stats:
            self.stats[model_name] = UsageStats()
        
        # Update counters
        self.stats[model_name] += UsageStats(metadata)

    def record_time(self, key: str, time: float):
        """
        Record the response time for a key. A key can be: a model name, or a special word, like "throttle".
        
        Args:
            key: Name of the LLM model or a key
            time: Time taken for the LLM call in seconds
        """
        if key not in self.time:
            self.time[key] = 0.0
        self.time[key] += time

    def record(self, model_name: str, metadata, response_time: float):
        """
        Soon to be deprecated. Record token usage and run time for a model.
        
        Args:
            model_name: Name of the LLM model
            metadata: Usage metadata object from the LLM response
            response_time: Time taken for the LLM call in seconds
        """
        self.record_usage(model_name, metadata)
        self.record_time(model_name, response_time)

    def record_function_call(self, model_name: str, function_name: str, success: bool):
        """
        Record a function call made by the LLM.
        
        Args:
            model_name: Name of the LLM model
            function_name: Name of the function called
            success: Whether the function call was successful
        """
        # This method can be expanded to track function call statistics if needed.
        # Initialize stats for new models
        if model_name not in self.stats:
            self.stats[model_name] = UsageStats()
        if function_name not in self.stats[model_name].function_calls:
            self.stats[model_name].function_calls[function_name] = {'count': 0, 'success': 0, 'failure': 0}
        self.stats[model_name].function_calls[function_name]['count'] += 1
        if success:
            self.stats[model_name].function_calls[function_name]['success'] += 1
        else:
            self.stats[model_name].function_calls[function_name]['failure'] += 1

        history_entry = {
            'model': model_name,
            'function': function_name,
            'success': success
        }
        self.call_history.append(history_entry)
    
    def print_call_info(self, metadata, response_time: float|None = None):
        """
        Print per-call token usage information.
        
        Args:
            metadata: Usage metadata object from the LLM response
            response_time: Time taken for the LLM call in seconds
        """
        print("Token Usage Info: total {}, cache {}, candidates {}, prompt {}, thoughts {}, tool_use {}".format(
            metadata.total_token_count or 0,
            metadata.cached_content_token_count or 0,
            metadata.candidates_token_count or 0,
            metadata.prompt_token_count or 0,
            metadata.thoughts_token_count or 0,
            metadata.tool_use_prompt_token_count or 0
        ))
        if response_time is not None:
            print(f"Time taken for LLM call: {response_time:.1f} seconds")

    def summary(self) -> list[str]:
        """
        Generate aggregated token usage statistics for all models.
        
        Returns:
            List of strings containing formatted statistics
        """
        if not self.stats:
            return ["\n📊 No LLM usage statistics to report."]
        
        lines = []
        lines.append("")
        lines.append("=" * 80)
        lines.append("📊 LLM Token Usage Summary")
        lines.append("=" * 80)
        
        for model_name, stats in sorted(self.stats.items()):
            if model_name in self.time:
                model_time = self.time[model_name]            
            else:
                model_time = 0.0
            avg_time = model_time / stats.llm_run_count if stats.llm_run_count > 0 else 0
            billable = stats.billable_tokens()
            lines.append("")
            lines.append(f"🤖 Model: {model_name}")
            lines.append(f"   Runs: {stats.llm_run_count}")
            lines.append(f"   Time: {model_time:.1f}s total, {avg_time:.1f}s avg per call")
            lines.append(f"   Total tokens: {stats.total_token_count:,}")
            lines.append(f"   ├─ Prompt: {stats.prompt_token_count:,}")
            lines.append(f"   ├─ Candidates: {stats.candidates_token_count:,}")
            lines.append(f"   ├─ Cached: {stats.cached_content_token_count:,}")
            lines.append(f"   ├─ Thoughts: {stats.thoughts_token_count:,}")
            lines.append(f"   └─ Tool use: {stats.tool_use_prompt_token_count:,}")
            lines.append(f"   Billable tokens:")
            lines.append(f"   ├─ Input: {billable['input']:,}")
            lines.append(f"   ├─ Output: {billable['output']:,}")
            lines.append(f"   └─ Cached: {billable['cached']:,}")
            if model_name in self.PRICING:
                pricing = self.PRICING[model_name]
                cost_input = (billable['input'] / 1_000_000) * pricing['input']
                cost_output = (billable['output'] / 1_000_000) * pricing['output']
                cost_cached = (billable['cached'] / 1_000_000) * pricing['cached']
                total_cost = cost_input + cost_output + cost_cached
                lines.append(f"   Estimated Cost: ${total_cost:.4f}")
                lines.append(f"   ├─ Input: ${cost_input:.4f}")
                lines.append(f"   ├─ Output: ${cost_output:.4f}")
                lines.append(f"   └─ Cached: ${cost_cached:.4f}")
            # Function call statistics
            if stats.function_calls:
                lines.append(f"   Function Calls:")
                for func_name, call_info in stats.function_calls.items():
                    lines.append(f"   ├─ {func_name}: {call_info['count']} calls (Success: {call_info['success']}, Failure: {call_info['failure']})")
        if self.call_history:
            lines.append(f"   Function Calls:")
            for entry in self.call_history:  # Show last 5 calls
                lines.append(f"   ├─ Function: {entry['function']}, Success: {entry['success']}")

        # Add grand totals
        total_runs = sum(s.llm_run_count for s in self.stats.values())
        total_tokens = sum(s.total_token_count for s in self.stats.values())
        
        lines.append("")
        lines.append("-" * 80)
        lines.append(f"📈 Grand Total: {total_runs} runs, {total_tokens:,} tokens")
        for key, total_time in self.time.items():
            lines.append(f"   {key} time: {total_time:.1f}s")
        lines.append("=" * 80)
        
        return lines
    
    def print_summary(self):
        """Print the aggregated token usage statistics for all models."""
        for line in self.summary():
            print(line)
