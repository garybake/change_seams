"""Web search tool — uses Tavily via langchain_community."""
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

from app.config import settings
from app.tools.base import ChangeSeamsTool, ToolContract


class SearchInput(BaseModel):
    query: str = Field(description="Search query string")


class SearchTool(ChangeSeamsTool):
    name: str = "search"
    description: str = (
        "Search the web for current information. Use this for factual questions "
        "about recent events, people, places, or anything that requires up-to-date knowledge."
    )
    args_schema: Type[BaseModel] = SearchInput
    contract: ToolContract = ToolContract(
        name="search",
        description="Web search via Tavily API.",
        args_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string"}
            },
            "required": ["query"],
        },
        required_permissions=["external_api", "read_web"],
    )

    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        if not settings.tavily_api_key:
            return "Search tool unavailable: TAVILY_API_KEY not configured."
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            import os

            os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
            tavily = TavilySearchResults(max_results=3)
            results = tavily.run(query)
            return str(results)
        except Exception as e:
            return f"Search failed: {e}"

    async def _arun(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        if not settings.tavily_api_key:
            return "Search tool unavailable: TAVILY_API_KEY not configured."
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            import os

            os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
            tavily = TavilySearchResults(max_results=3)
            results = await tavily.arun(query)
            return str(results)
        except Exception as e:
            return f"Search failed: {e}"
