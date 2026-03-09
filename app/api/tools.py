"""GET /api/tools — exposes the tool contract registry."""
from fastapi import APIRouter

from app.tools import TOOL_REGISTRY

router = APIRouter()


@router.get("/api/tools", tags=["tools"])
def list_tools() -> list[dict]:
    return [
        {
            "name": tool.contract.name,
            "description": tool.contract.description,
            "args_schema": tool.contract.args_schema,
            "required_permissions": tool.contract.required_permissions,
        }
        for tool in TOOL_REGISTRY.values()
    ]
