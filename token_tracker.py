"""
Token usage tracking for LLM API calls.

This module provides the TokenUsageTracker class for tracking and reporting
token usage statistics across multiple LLM models.
"""


class TokenUsageTracker:
    """Tracks token usage statistics across multiple LLM models."""
    
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
            self.stats[model_name] = {
                'total_token_count': 0,
                'cached_content_token_count': 0,
                'candidates_token_count': 0,
                'prompt_token_count': 0,
                'thoughts_token_count': 0,
                'tool_use_prompt_token_count': 0,
                'llm_run_count': 0,
                'total_time': 0.0
            }
        
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
    
    def print_summary(self):
        """Print aggregated token usage statistics for all models."""
        if not self.stats:
            print("\n📊 No LLM usage statistics to report.")
            return
        
        print("\n" + "=" * 80)
        print("📊 LLM Token Usage Summary")
        print("=" * 80)
        
        for model_name, stats in sorted(self.stats.items()):
            avg_time = stats['total_time'] / stats['llm_run_count'] if stats['llm_run_count'] > 0 else 0
            print(f"\n🤖 Model: {model_name}")
            print(f"   Runs: {stats['llm_run_count']}")
            print(f"   Time: {stats['total_time']:.1f}s total, {avg_time:.1f}s avg per call")
            print(f"   Total tokens: {stats['total_token_count']:,}")
            print(f"   ├─ Prompt: {stats['prompt_token_count']:,}")
            print(f"   ├─ Candidates: {stats['candidates_token_count']:,}")
            print(f"   ├─ Cached: {stats['cached_content_token_count']:,}")
            print(f"   ├─ Thoughts: {stats['thoughts_token_count']:,}")
            print(f"   └─ Tool use: {stats['tool_use_prompt_token_count']:,}")
        
        # Print grand totals
        total_runs = sum(s['llm_run_count'] for s in self.stats.values())
        total_tokens = sum(s['total_token_count'] for s in self.stats.values())
        total_time = sum(s['total_time'] for s in self.stats.values())
        
        print("\n" + "-" * 80)
        print(f"📈 Grand Total: {total_runs} runs, {total_tokens:,} tokens, {total_time:.1f}s")
        print("=" * 80)
