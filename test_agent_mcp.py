#!/usr/bin/env python3
"""
Simple test to verify the agent-based code generation with MCP integration works.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coding_agent import code, Context, load_task_config, DEFAULT_TASK_CONFIG

def test_agent_mcp_integration():
    """Test that the code function can use MCP server via agent"""
    
    # Create a temporary test context
    test_dir = tempfile.mkdtemp(prefix="test_agent_mcp_")
    print(f"📁 Test directory: {test_dir}")
    
    try:
        # Create a minimal context
        context = Context(
            filename="test_agent",
            use_case="Create a simple Python function that adds two numbers",
            goals="The function should be named 'add' and take two parameters"
        )
        
        # Initialize with empty research summary
        context.research_summary = "No research needed for this simple task"
        
        # Start first iteration
        context.start_iteration()
        
        # Use minimal config for testing
        config = DEFAULT_TASK_CONFIG.copy()
        config["coder_model"] = "gemini-2.5-flash"  # Use faster model for testing
        
        print("\n🧪 Testing agent-based code generation with MCP...")
        # Note: mcp_pipes parameter is optional, will use None for testing without MCP
        result = code(config, context, mcp_pipes=None, use_diffs=False)
        
        if result:
            print("✅ Code generation successful!")
            print(f"📄 Generated code ({len(context.current.code)} lines)")
            if context.current.code:
                print("\n--- Generated Code ---")
                for i, line in enumerate(context.current.code[:10], 1):
                    print(f"{i:3d}: {line}")
                if len(context.current.code) > 10:
                    print(f"... ({len(context.current.code) - 10} more lines)")
            
            # Check if agent flag was set
            if 'agent_used_mcp' in context.current.flags:
                print("✅ Agent used MCP tools")
            else:
                print("⚠️  Agent flag not set")
            
            return True
        else:
            print("❌ Code generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        print(f"\n🧹 Cleaned up test directory")

if __name__ == "__main__":
    print("🚀 Starting MCP Agent Integration Test\n")
    success = test_agent_mcp_integration()
    sys.exit(0 if success else 1)
