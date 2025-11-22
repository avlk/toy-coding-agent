"""
Unit tests for token_tracker.py module.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from token_tracker import TokenUsageTracker


class MockMetadata:
    """Mock metadata object for testing."""
    def __init__(self, total=100, cached=10, candidates=50, prompt=30, thoughts=5, tool_use=5):
        self.total_token_count = total
        self.cached_content_token_count = cached
        self.candidates_token_count = candidates
        self.prompt_token_count = prompt
        self.thoughts_token_count = thoughts
        self.tool_use_prompt_token_count = tool_use


class TestTokenUsageTracker:
    """Tests for TokenUsageTracker class."""
    
    def test_initialization(self):
        tracker = TokenUsageTracker()
        assert tracker.stats == {}
    
    def test_record_new_model(self):
        tracker = TokenUsageTracker()
        metadata = MockMetadata()
        tracker.record("test-model", metadata, 1.5)
        
        assert "test-model" in tracker.stats
        assert tracker.stats["test-model"]["total_token_count"] == 100
        assert tracker.stats["test-model"]["llm_run_count"] == 1
        assert tracker.stats["test-model"]["total_time"] == 1.5
    
    def test_record_multiple_calls(self):
        tracker = TokenUsageTracker()
        metadata1 = MockMetadata(total=100, prompt=30)
        metadata2 = MockMetadata(total=150, prompt=50)
        
        tracker.record("test-model", metadata1, 1.0)
        tracker.record("test-model", metadata2, 2.0)
        
        assert tracker.stats["test-model"]["total_token_count"] == 250
        assert tracker.stats["test-model"]["prompt_token_count"] == 80
        assert tracker.stats["test-model"]["llm_run_count"] == 2
        assert tracker.stats["test-model"]["total_time"] == 3.0
    
    def test_record_multiple_models(self):
        tracker = TokenUsageTracker()
        metadata1 = MockMetadata(total=100)
        metadata2 = MockMetadata(total=200)
        
        tracker.record("model-1", metadata1, 1.0)
        tracker.record("model-2", metadata2, 2.0)
        
        assert len(tracker.stats) == 2
        assert tracker.stats["model-1"]["total_token_count"] == 100
        assert tracker.stats["model-2"]["total_token_count"] == 200
    
    def test_record_with_none_values(self):
        """Test handling of None values in metadata."""
        class NoneMetadata:
            total_token_count = None
            cached_content_token_count = None
            candidates_token_count = None
            prompt_token_count = None
            thoughts_token_count = None
            tool_use_prompt_token_count = None
        
        tracker = TokenUsageTracker()
        tracker.record("test-model", NoneMetadata(), 1.0)
        
        assert tracker.stats["test-model"]["total_token_count"] == 0
        assert tracker.stats["test-model"]["llm_run_count"] == 1
    
    def test_summary_empty_stats(self):
        tracker = TokenUsageTracker()
        summary = tracker.summary()
        
        assert isinstance(summary, list)
        assert len(summary) == 1
        assert "No LLM usage statistics" in summary[0]
    
    def test_summary_with_data(self):
        tracker = TokenUsageTracker()
        metadata = MockMetadata(total=1000, prompt=300, candidates=500)
        tracker.record("test-model", metadata, 5.0)
        
        summary = tracker.summary()
        
        assert isinstance(summary, list)
        assert any("test-model" in line for line in summary)
        assert any("1000" in line or "1,000" in line for line in summary)  # Total tokens (formatted or not)
        assert any("5.0s" in line for line in summary)  # Total time
    
    def test_summary_multiple_models(self):
        tracker = TokenUsageTracker()
        tracker.record("model-a", MockMetadata(total=500), 2.0)
        tracker.record("model-b", MockMetadata(total=300), 1.5)
        
        summary = tracker.summary()
        summary_text = "\n".join(summary)
        
        assert "model-a" in summary_text
        assert "model-b" in summary_text
        assert "Grand Total" in summary_text
        assert "800" in summary_text  # Total tokens across models
    
    def test_summary_average_time(self):
        tracker = TokenUsageTracker()
        tracker.record("test-model", MockMetadata(), 2.0)
        tracker.record("test-model", MockMetadata(), 4.0)
        
        summary = tracker.summary()
        summary_text = "\n".join(summary)
        
        assert "3.0s avg" in summary_text  # Average of 2.0 and 4.0
    
    def test_print_call_info(self, capsys):
        """Test print_call_info output."""
        tracker = TokenUsageTracker()
        metadata = MockMetadata(total=100, cached=10, candidates=50, prompt=30)
        
        tracker.print_call_info(metadata, 2.5)
        captured = capsys.readouterr()
        
        assert "Token Usage Info" in captured.out
        assert "100" in captured.out
        assert "2.5 seconds" in captured.out
    
    def test_print_summary(self, capsys):
        """Test print_summary output."""
        tracker = TokenUsageTracker()
        tracker.record("test-model", MockMetadata(total=500), 3.0)
        
        tracker.print_summary()
        captured = capsys.readouterr()
        
        assert "LLM Token Usage Summary" in captured.out
        assert "test-model" in captured.out
        assert "500" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
