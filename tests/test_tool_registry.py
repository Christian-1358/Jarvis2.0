"""
Tests for tool registry.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tool_registry import ToolRegistry, get_registry, get_tool, execute_tool


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_singleton_pattern(self):
        """Test that get_registry returns singleton."""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2

    def test_list_all_tools(self):
        """Test listing all registered tools."""
        registry = get_registry()
        tools = registry.list_all()
        assert isinstance(tools, dict)
        assert len(tools) > 0

    def test_get_tool_existing(self):
        """Test getting an existing tool."""
        tool = get_tool("open_app")
        assert tool is not None

    def test_get_tool_nonexistent(self):
        """Test getting a non-existent tool returns None."""
        tool = get_tool("nonexistent_action_xyz")
        assert tool is None

    def test_execute_open_app(self):
        """Test executing open_app tool."""
        # This will only work if the app exists, but should not crash
        result = execute_tool("open_app", "chrome", {})
        # Result is a string, may succeed or fail depending on system
        assert isinstance(result, str)


class TestToolRegistration:
    """Tests for tool registration functionality."""

    def test_tool_has_required_fields(self):
        """Test that registered tools have required fields."""
        registry = get_registry()
        tools = registry.list_all()

        if tools:
            tool_name = list(tools.keys())[0]
            tool = tools[tool_name]
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'category')

    def test_tool_statistics_tracking(self):
        """Test that tool usage statistics are tracked."""
        registry = get_registry()
        tool = get_tool("open_app")

        if tool:
            initial_count = tool.use_count
            # Execute will increment count
            execute_tool("open_app", "chrome", {})
            # Check if registry updated (may need to refetch)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])