# Jarvis MiniMax - Core Module
# Arquitetura centralizada de ferramentas e decisões

from .minimax_client import MiniMaxClient, analyze_command
from .tool_registry import (
    ToolRegistry,
    Tool,
    get_registry,
    get_tool,
    execute_tool,
    list_tools
)
from .safety import (
    SafetyManager,
    get_safety,
    is_dangerous,
    requires_confirmation,
    request_confirmation,
    check_confirmation
)

__all__ = [
    # MiniMax Client
    "MiniMaxClient",
    "analyze_command",
    # Tool Registry
    "ToolRegistry",
    "Tool",
    "get_registry",
    "get_tool",
    "execute_tool",
    "list_tools",
    # Safety
    "SafetyManager",
    "get_safety",
    "is_dangerous",
    "requires_confirmation",
    "request_confirmation",
    "check_confirmation",
]