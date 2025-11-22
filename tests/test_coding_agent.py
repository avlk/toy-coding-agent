"""
Unit tests for coding_agent.py - Pure logic tests (no LLM mocking)
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

# Import classes and functions from coding_agent
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from coding_agent import Iteration, Context, load_task_config, progress_check, format_final_code, create_filename


class TestIteration:
    """Tests for the Iteration class"""
    
    def test_iteration_initial_state(self):
        """Test that Iteration initializes with all None/empty values"""
        iteration = Iteration()
        
        assert iteration.code is None
        assert iteration.feedback is None
        assert iteration.flags == set()
        assert iteration.program_output is None
        assert iteration.score is None
        
    def test_add_flags(self):
        """Test adding flags"""
        iteration = Iteration()
        iteration.add_flag('syntax_error')
        iteration.add_flag('exec_success')
        iteration.add_flag('llm_executed')
        
        assert iteration.flags == {'syntax_error', 'exec_success', 'llm_executed'}
    
    def test_add_flags_accumulates(self):
        """Test that flags accumulate and don't reset"""
        iteration = Iteration()
        iteration.add_flag('first')
        assert len(iteration.flags) == 1
        
        iteration.add_flag('second')
        assert len(iteration.flags) == 2
        assert 'first' in iteration.flags
        assert 'second' in iteration.flags
    
    def test_get_score_with_value(self):
        """Test get_score returns the score when set"""
        iteration = Iteration()
        iteration.score = 75
        
        assert iteration.get_score() == 75
    
    def test_get_score_when_none(self):
        """Test get_score returns 0 when score is None"""
        iteration = Iteration()
        assert iteration.score is None
        
        assert iteration.get_score() == 0


class TestContext:
    """Tests for the Context class"""
    
    def test_context_initial_state(self):
        """Test Context initializes correctly"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        
        assert ctx.filename == 'test'
        assert ctx.use_case == 'UC'
        assert ctx.goals == 'Goals'
        assert ctx.iterations == []
        assert ctx.current_iteration is None
    
    def test_previous_with_iterations(self):
        """Test previous property returns last iteration"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create iterations using start_iteration
        ctx.start_iteration()
        ctx.current.code = "code1"
        ctx.start_iteration()
        ctx.current.code = "code2"
        
        assert ctx.previous is not None
        assert ctx.previous.code == "code1"
    
    def test_current_throws_if_none(self):
        """Test current property throws exception if current_iteration is None"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        ctx.current_iteration = None
        
        with pytest.raises(Exception, match="Start an iteration"):
            _ = ctx.current
    
    def test_current_returns_existing(self):
        """Test current property returns existing iteration"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        ctx.start_iteration()
        ctx.current.code = "test_code"
        
        result = ctx.current
        
        assert isinstance(result, Iteration)
        assert result.code == "test_code"
    
    def test_iter_no_with_empty_iterations(self):
        """Test iter_no returns 1 when no iterations"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        
        assert ctx.iter_no == 1
    
    def test_iter_no_with_iterations(self):
        """Test iter_no returns correct count"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 3 completed iterations
        ctx.start_iteration()
        ctx.start_iteration()
        ctx.start_iteration()
        ctx.start_iteration()  # 4th iteration now current
        
        assert ctx.iter_no == 4  # 3 completed + 1 current
    
    def test_start_iteration(self):
        """Test start_iteration appends current and creates new"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        ctx.start_iteration()
        current_before = ctx.current
        current_before.code = "test"
        
        ctx.start_iteration()
        
        assert len(ctx.iterations) == 1
        assert ctx.iterations[0] is current_before
        assert ctx.iterations[0].code == "test"
        assert ctx.current is not current_before
        assert isinstance(ctx.current, Iteration)
    
    def test_erase_iteration(self):
        """Test erase_iteration clears current without saving"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 2 completed iterations
        ctx.start_iteration()
        ctx.start_iteration()
        ctx.start_iteration()  # 3rd is current
        ctx.current.code = "test"
        
        ctx.erase_iteration()
        
        assert len(ctx.iterations) == 2  # Not changed
        assert ctx.current_iteration is None  # Cleared
    
    def test_trim_iterations(self):
        """Test trim_iterations keeps only first N"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 10 iterations using start_iteration
        for i in range(10):
            ctx.start_iteration()
            ctx.current.code = f"code_{i}"
        ctx.start_iteration()  # Move all to iterations list
        
        ctx.trim_iterations(3)
        
        assert len(ctx.iterations) == 3
        assert ctx.iterations[0].code == "code_0"
        assert ctx.iterations[1].code == "code_1"
        assert ctx.iterations[2].code == "code_2"
    
    def test_trim_iterations_when_less_than_n(self):
        """Test trim_iterations does nothing when iterations < n"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 2 iterations
        ctx.start_iteration()
        ctx.start_iteration()
        ctx.start_iteration()  # Move both to iterations list
        
        ctx.trim_iterations(5)
        
        assert len(ctx.iterations) == 2
    
    def test_save_to_with_name_placeholder(self):
        """Test save_to replaces {name} placeholder and saves file"""
        ctx = Context(filename='myfile', use_case='UC', goals='Goals')
        ctx.start_iteration()  # Need to start iteration for iter_no
        
        ctx.save_to("{name}_output.txt", "test content")
        
        # Verify file was created
        expected_path = Path("solutions/myfile_output.txt")
        assert expected_path.exists()
    
    def test_save_to_with_iter_placeholder(self):
        """Test save_to replaces {iter} placeholder and saves file"""
        ctx = Context(filename='myfile', use_case='UC', goals='Goals')
        # Create 2 iterations to get iter_no = 3
        ctx.start_iteration()
        ctx.start_iteration()
        ctx.start_iteration()  # iter_no will be 3
        
        ctx.save_to("file_v{iter}.py", "test content")
        
        # Verify file was created
        expected_path = Path("solutions/file_v3.py")
        assert expected_path.exists()
    
    def test_save_to_with_both_placeholders(self):
        """Test save_to replaces both {name} and {iter} and saves file"""
        ctx = Context(filename='qrcode', use_case='UC', goals='Goals')
        # Create 1 iteration to get iter_no = 2
        ctx.start_iteration()
        ctx.start_iteration()  # iter_no will be 2
        
        ctx.save_to("{name}_code_v{iter}.py", "code here")
        
        # Verify file was created
        expected_path = Path("solutions/qrcode_code_v2.py")
        assert expected_path.exists()
        
        ctx.save_to("{name}_code_v{iter}.py", "code here")
        
        # Verify file was created
        expected_path = Path("solutions/qrcode_code_v2.py")
        assert expected_path.exists()


class TestLoadTaskConfig:
    """Tests for load_task_config function"""
    
    def test_load_task_config_file_not_exists(self):
        """Test returns default config when file doesn't exist"""
        with patch('pathlib.Path.exists', return_value=False):
            config = load_task_config('nonexistent.json')
        
        # Check default values (see coding_agent.py DEFAULT_TASK_CONFIG)
        assert config['coder_model'] == 'gemini-2.5-pro'
        assert config['reviewer_model'] == 'gemini-2.5-pro'
        assert 'max_rounds' in config  # Not max_iterations
        assert 'sandbox_method' in config  # Not sandbox
    
    def test_load_task_config_merges_with_defaults(self):
        """Test loaded config merges with defaults"""
        mock_config = '{"coder_model": "custom-model", "max_rounds": 20}'
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=mock_config)):
                config = load_task_config('task.json')
        
        # Custom values
        assert config['coder_model'] == 'custom-model'
        assert config['max_rounds'] == 20
        
        # Default values still present
        assert 'reviewer_model' in config
    
    def test_load_task_config_json_parse_error(self):
        """Test returns default config on JSON parse error"""
        mock_invalid_json = '{"invalid": json content}'
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=mock_invalid_json)):
                config = load_task_config('task.json')
        
        # Should return defaults
        assert 'coder_model' in config
        assert 'max_rounds' in config
    
    def test_load_task_config_preserves_all_keys(self):
        """Test all default keys are present in result"""
        with patch('pathlib.Path.exists', return_value=False):
            config = load_task_config('test.json')
        
        # Check that common expected keys exist
        assert 'coder_model' in config
        assert 'reviewer_model' in config
        assert 'utility_model' in config
        assert 'max_rounds' in config
        assert 'sandbox_method' in config


class TestProgressCheck:
    """Tests for progress_check function"""
    
    def test_progress_check_less_than_3_iterations(self):
        """Test returns None when less than 3 iterations"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 2 iterations
        ctx.start_iteration()
        ctx.current.score = 50
        ctx.start_iteration()
        ctx.current.score = 40
        ctx.start_iteration()
        ctx.current.score = 45
        
        result = progress_check(ctx)
        
        assert result is None
    
    def test_progress_check_best_is_recent(self):
        """Test returns None when best score is within last 3 iterations"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 5 iterations with scores
        scores = [30, 40, 50, 60, 55]
        for score in scores:
            ctx.start_iteration()
            ctx.current.score = score
        ctx.start_iteration()
        ctx.current.score = 50
        
        result = progress_check(ctx)
        
        assert result is None
    
    def test_progress_check_best_is_old(self):
        """Test returns iteration index when best score is old"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 7 iterations with scores
        scores = [60, 50, 40, 35, 30, 25, 20]
        for score in scores:
            ctx.start_iteration()
            ctx.current.score = score
        ctx.start_iteration()
        ctx.current.score = 15
        
        result = progress_check(ctx)
        
        assert result == 0  # Index of best score
    
    def test_progress_check_finds_rightmost_best(self):
        """Test finds rightmost best score when duplicates exist"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 6 iterations with duplicate best scores
        scores = [60, 60, 50, 40, 30, 20]
        for score in scores:
            ctx.start_iteration()
            ctx.current.score = score
        ctx.start_iteration()
        ctx.current.score = 15
        
        result = progress_check(ctx)
        
        assert result == 1  # Rightmost best score index
    
    def test_progress_check_exactly_3_iterations_old(self):
        """Test boundary case: best is exactly 3 iterations old"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 7 iterations
        scores = [70, 60, 50, 80, 40, 30, 20]
        for score in scores:
            ctx.start_iteration()
            ctx.current.score = score
        ctx.start_iteration()
        ctx.current.score = 15
        
        result = progress_check(ctx)
        
        # With 8 total scores (7 iterations + current), best at index 3
        # best_index (3) < len(scores) - 3 (5) is True, so should return index
        assert result == 3
    
    def test_progress_check_exactly_4_iterations_old(self):
        """Test boundary case: best is exactly 4 iterations old"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 8 iterations
        scores = [70, 60, 50, 80, 40, 30, 20, 10]
        for score in scores:
            ctx.start_iteration()
            ctx.current.score = score
        ctx.start_iteration()
        ctx.current.score = 5
        
        result = progress_check(ctx)
        
        # Should return index as best is >3 from end
        assert result == 3
    
    def test_progress_check_handles_none_scores(self):
        """Test that None scores are treated as 0 via get_score()"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 5 iterations with some None scores
        scores = [None, 50, 60, None, 55]
        for score in scores:
            ctx.start_iteration()
            ctx.current.score = score
        ctx.start_iteration()
        ctx.current.score = 50
        
        # Should not crash, None values treated as 0
        result = progress_check(ctx)
        
        # Scores: [0, 50, 60, 0, 55, 50] - 6 total, best (60) at index 2
        # best_index (2) < len(scores) - 3 (3) is True, so returns 2
        assert result == 2


class TestFormatFinalCode:
    """Tests for format_final_code function"""
    
    def test_format_final_code_basic(self):
        """Test basic header generation"""
        ctx = Context(filename='test', use_case='Generate QR codes', goals='Create QR from text')
        ctx.start_iteration()
        ctx.current.code = "print('hello')\nprint('world')"
        config = {'coder_model': 'model-a', 'reviewer_model': 'model-b', 'utility_model': 'model-c'}
        
        mock_tracker = Mock()
        mock_tracker.summary.return_value = ["Total: 1000 tokens"]
        
        result = format_final_code(config, ctx, mock_tracker)
        
        # result is a list of lines
        result_text = '\n'.join(result)
        
        # Check header content
        assert "Generate QR codes" in result_text
        assert "Create QR from text" in result_text
        assert "model-a" in result_text
        assert "model-b" in result_text
        assert "1 coding rounds" in result_text
        assert "Total: 1000 tokens" in result_text
        
        # Check code is appended
        assert "print('hello')" in result_text
        assert "print('world')" in result_text
    
    def test_format_final_code_multiple_iterations(self):
        """Test iteration count with multiple iterations"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        # Create 3 iterations, then start the 4th
        for _ in range(3):
            ctx.start_iteration()
        ctx.start_iteration()
        ctx.current.code = "code"
        config = {'coder_model': 'model-a', 'reviewer_model': 'model-b', 'utility_model': 'model-c'}
        
        mock_tracker = Mock()
        mock_tracker.summary.return_value = ["Tokens: 500"]
        
        result = format_final_code(config, ctx, mock_tracker)
        
        result_text = '\n'.join(result)
        assert "4 coding rounds" in result_text
    
    def test_format_final_code_preserves_code(self):
        """Test code lines are preserved exactly"""
        ctx = Context(filename='test', use_case='UC', goals='Goals')
        code_lines = [
            "import os",
            "def main():",
            "    print('test')",
            "    return 42",
            "",
            "if __name__ == '__main__':",
            "    main()"
        ]
        ctx.start_iteration()
        ctx.current.code = "\n".join(code_lines)
        config = {'coder_model': 'model-a', 'reviewer_model': 'model-b', 'utility_model': 'model-c'}
        
        mock_tracker = Mock()
        mock_tracker.summary.return_value = []
        
        result = format_final_code(config, ctx, mock_tracker)
        
        # result is a list of lines, join them
        result_text = '\n'.join(result)
        
        # All code lines should be in result
        for line in code_lines:
            assert line in result_text


class TestCreateFilename:
    """Tests for create_filename function"""
    
    def test_create_filename_format(self):
        """Test filename format is {basename}_{4digits}"""
        result = create_filename('myfile')
        
        # Should be myfile_XXXX where XXXX is 4 digits
        assert result.startswith('myfile_')
        suffix = result.replace('myfile_', '')
        assert len(suffix) == 4
        assert suffix.isdigit()
    
    def test_create_filename_range(self):
        """Test random suffix is in range 1000-9999"""
        # Run multiple times to check range
        for _ in range(20):
            result = create_filename('test')
            suffix = result.replace('test_', '')
            number = int(suffix)
            
            assert 1000 <= number <= 9999
    
    def test_create_filename_different_basenames(self):
        """Test works with different basenames"""
        basenames = ['qrcode', 'solution', 'test_file', 'abc']
        
        for basename in basenames:
            result = create_filename(basename)
            assert result.startswith(f'{basename}_')
            suffix = result.replace(f'{basename}_', '')
            assert len(suffix) == 4
            assert suffix.isdigit()
