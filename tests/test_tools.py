"""Tests for Seam 3: tool contract layer."""
import pytest
import respx
import httpx


def test_echo_tool_returns_input():
    from app.tools.echo import EchoTool

    tool = EchoTool()
    result = tool._run(text="hello world")
    assert result == "Echo: hello world"


def test_echo_tool_has_empty_permissions():
    from app.tools.echo import EchoTool

    tool = EchoTool()
    assert tool.contract.required_permissions == []


def test_echo_tool_has_args_schema():
    from app.tools.echo import EchoTool

    tool = EchoTool()
    schema = tool.contract.args_schema
    assert schema["type"] == "object"
    assert "text" in schema["properties"]


def test_weather_tool_no_api_key(monkeypatch):
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "")
    from importlib import reload
    import app.config as cfg_mod
    import app.tools.weather as wt_mod

    reload(cfg_mod)
    reload(wt_mod)

    tool = wt_mod.WeatherTool()
    result = tool._run(location="Dublin")
    assert "unavailable" in result.lower()


@respx.mock
def test_weather_tool_success(monkeypatch):
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key")
    from importlib import reload
    import app.config as cfg_mod
    import app.tools.weather as wt_mod

    reload(cfg_mod)
    reload(wt_mod)

    respx.get("https://api.openweathermap.org/data/2.5/weather").mock(
        return_value=httpx.Response(
            200,
            json={
                "main": {"temp": 12.5},
                "weather": [{"description": "cloudy"}],
                "name": "Dublin",
                "sys": {"country": "IE"},
            },
        )
    )

    tool = wt_mod.WeatherTool()
    result = tool._run(location="Dublin")
    assert "Dublin" in result
    assert "12.5" in result
    assert "cloudy" in result


@respx.mock
def test_weather_tool_404(monkeypatch):
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key")
    from importlib import reload
    import app.config as cfg_mod
    import app.tools.weather as wt_mod

    reload(cfg_mod)
    reload(wt_mod)

    respx.get("https://api.openweathermap.org/data/2.5/weather").mock(
        return_value=httpx.Response(404)
    )

    tool = wt_mod.WeatherTool()
    result = tool._run(location="Nonexistent City XYZ")
    assert "not found" in result.lower()


def test_search_tool_no_api_key(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    from importlib import reload
    import app.config as cfg_mod
    import app.tools.search as st_mod

    reload(cfg_mod)
    reload(st_mod)

    tool = st_mod.SearchTool()
    result = tool._run(query="test query")
    assert "unavailable" in result.lower()


def test_tool_registry_contains_all_tools():
    from app.tools import TOOL_REGISTRY

    assert "echo" in TOOL_REGISTRY
    assert "weather" in TOOL_REGISTRY
    assert "search" in TOOL_REGISTRY


def test_get_enabled_tools_filters_registry():
    from app.tools import get_enabled_tools

    tools = get_enabled_tools(["echo"])
    assert len(tools) == 1
    assert tools[0].name == "echo"


def test_get_enabled_tools_skips_unknown():
    from app.tools import get_enabled_tools

    tools = get_enabled_tools(["echo", "nonexistent"])
    assert len(tools) == 1


def test_get_enabled_tools_filters_by_permission():
    from app.tools import get_enabled_tools

    # empty allowed_permissions: only echo (no required permissions) survives
    tools = get_enabled_tools(["echo", "weather", "search"], allowed_permissions=set())
    assert len(tools) == 1
    assert tools[0].name == "echo"


def test_get_enabled_tools_default_allows_all():
    from app.tools import get_enabled_tools

    tools = get_enabled_tools(
        ["echo", "weather", "search"],
        allowed_permissions={"external_api", "read_web"},
    )
    assert len(tools) == 3


@pytest.mark.anyio
async def test_tools_endpoint_lists_all_registered(client):
    response = await client.get("/api/tools")
    assert response.status_code == 200
    data = response.json()
    names = {t["name"] for t in data}
    assert names == {"echo", "weather", "search"}
    for tool in data:
        assert "name" in tool
        assert "description" in tool
        assert "args_schema" in tool
        assert "required_permissions" in tool


@pytest.mark.anyio
async def test_tools_endpoint_contract_shape(client):
    response = await client.get("/api/tools")
    data = response.json()
    for tool in data:
        schema = tool["args_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
