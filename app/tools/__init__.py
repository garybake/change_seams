"""
Tool registry — all tools auto-register on import.
get_enabled_tools() reads ENABLED_TOOLS from config to filter the registry.
"""
from app.tools.base import ChangeSeamsTool, ToolContract

TOOL_REGISTRY: dict[str, ChangeSeamsTool] = {}


def register(tool: ChangeSeamsTool) -> None:
    TOOL_REGISTRY[tool.name] = tool


def get_enabled_tools(
    enabled_names: list[str],
    allowed_permissions: set[str] | None = None,
) -> list[ChangeSeamsTool]:
    tools = [TOOL_REGISTRY[n] for n in enabled_names if n in TOOL_REGISTRY]
    if allowed_permissions is not None:
        tools = [
            t for t in tools
            if set(t.contract.required_permissions).issubset(allowed_permissions)
        ]
    return tools


# Import all tool modules to trigger registration
from app.tools.echo import EchoTool  # noqa: E402
from app.tools.weather import WeatherTool  # noqa: E402
from app.tools.search import SearchTool  # noqa: E402

register(EchoTool())
register(WeatherTool())
register(SearchTool())

__all__ = ["TOOL_REGISTRY", "register", "get_enabled_tools", "ToolContract", "ChangeSeamsTool"]
