"""
Seam 3 — Tool Contract Layer.

Every tool declares a ToolContract: name, description, args JSON schema,
and required_permissions. The ENABLED_TOOLS env var gates which tools the
agent can call at runtime.
"""
from dataclasses import dataclass, field
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import ConfigDict


@dataclass
class ToolContract:
    """Metadata contract every tool must declare."""

    name: str
    description: str
    args_schema: dict[str, Any]  # JSON Schema object
    required_permissions: list[str] = field(default_factory=list)


class ChangeSeamsTool(BaseTool):
    """Base class for all tools. Adds ToolContract metadata to LangChain's BaseTool."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    contract: ToolContract

    def get_contract(self) -> ToolContract:
        return self.contract
