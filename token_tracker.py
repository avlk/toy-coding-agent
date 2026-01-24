"""
Token usage tracking for LLM API calls.

This module provides the TokenUsageTracker class for tracking and reporting
token usage statistics across multiple LLM models.
"""


class TokenUsageTracker:
    """Tracks token usage statistics across multiple LLM models."""
    EMPTY_STATS = {
        'total_token_count': 0,
        'cached_content_token_count': 0,
        'candidates_token_count': 0,
        'prompt_token_count': 0,
        'thoughts_token_count': 0,
        'tool_use_prompt_token_count': 0,
        'llm_run_count': 0,
        'total_time': 0.0
    }

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
    
    def record(self, model_name: str, metadata, response_time: float):
        """
        Record token usage for a model.
        
        Args:
            model_name: Name of the LLM model
            metadata: Usage metadata object from the LLM response
            response_time: Time taken for the LLM call in seconds
        """
        # Initialize stats for new models
        if model_name not in self.stats:
            self.stats[model_name] = TokenUsageTracker.EMPTY_STATS.copy()
        
        # Update counters
        stats = self.stats[model_name]
        stats['total_token_count'] += metadata.total_token_count or 0
        stats['cached_content_token_count'] += metadata.cached_content_token_count or 0
        stats['candidates_token_count'] += metadata.candidates_token_count or 0
        stats['prompt_token_count'] += metadata.prompt_token_count or 0
        stats['thoughts_token_count'] += metadata.thoughts_token_count or 0
        stats['tool_use_prompt_token_count'] += metadata.tool_use_prompt_token_count or 0
        stats['llm_run_count'] += 1
        stats['total_time'] += response_time

    def record_time(self, model_name: str, response_time: float):
        """
        Record only the response time for a model.
        
        Args:
            model_name: Name of the LLM model
            response_time: Time taken for the LLM call in seconds
        """
        # Initialize stats for new models
        if model_name not in self.stats:
            self.stats[model_name] = TokenUsageTracker.EMPTY_STATS.copy()
        
        # Update time counter
        stats = self.stats[model_name]
        stats['total_time'] += response_time
    
    def print_call_info(self, metadata, response_time: float):
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
        print(f"Time taken for LLM call: {response_time:.1f} seconds")
    
    def billable_tokens(self, stat_item) -> dict[str, int]:
        """
        Get billable token counts from a statistics item.
        
        Args:
            stat_item: A statistics dictionary for a model

        Returns:
            Dictionary with billable token counts
        """     
        input = stat_item['prompt_token_count'] + stat_item['tool_use_prompt_token_count']
        output =  stat_item['candidates_token_count'] + stat_item['thoughts_token_count']
        cached = stat_item['cached_content_token_count']
        input -= cached
        return {
            'cached': cached,
            'input': input,
            'output': output,
        }

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
            avg_time = stats['total_time'] / stats['llm_run_count'] if stats['llm_run_count'] > 0 else 0
            billable = self.billable_tokens(stats)
            lines.append("")
            lines.append(f"🤖 Model: {model_name}")
            lines.append(f"   Runs: {stats['llm_run_count']}")
            lines.append(f"   Time: {stats['total_time']:.1f}s total, {avg_time:.1f}s avg per call")
            lines.append(f"   Total tokens: {stats['total_token_count']:,}")
            lines.append(f"   ├─ Prompt: {stats['prompt_token_count']:,}")
            lines.append(f"   ├─ Candidates: {stats['candidates_token_count']:,}")
            lines.append(f"   ├─ Cached: {stats['cached_content_token_count']:,}")
            lines.append(f"   ├─ Thoughts: {stats['thoughts_token_count']:,}")
            lines.append(f"   └─ Tool use: {stats['tool_use_prompt_token_count']:,}")
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
        
        # Add grand totals
        total_runs = sum(s['llm_run_count'] for s in self.stats.values())
        total_tokens = sum(s['total_token_count'] for s in self.stats.values())
        total_time = sum(s['total_time'] for s in self.stats.values())
        
        lines.append("")
        lines.append("-" * 80)
        lines.append(f"📈 Grand Total: {total_runs} runs, {total_tokens:,} tokens, {total_time:.1f}s")
        lines.append("=" * 80)
        
        return lines
    
    def print_summary(self):
        """Print the aggregated token usage statistics for all models."""
        for line in self.summary():
            print(line)
