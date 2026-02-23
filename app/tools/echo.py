"""Echo tool — no external dependencies, no permissions required."""
from typing import Any, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

from app.tools.base import ChangeSeamsTool, ToolContract


class EchoInput(BaseModel):
    text: str = Field(description="The text to echo back")


class EchoTool(ChangeSeamsTool):
    name: str = "echo"
    description: str = "Echoes back the input text. Useful for testing the tool contract pipeline."
    args_schema: Type[BaseModel] = EchoInput
    contract: ToolContract = ToolContract(
        name="echo",
        description="Echoes back the input text.",
        args_schema={
            "type": "object",
            "properties": {"text": {"type": "string", "description": "The text to echo back"}},
            "required": ["text"],
        },
        required_permissions=[],
    )

    def _run(
        self, text: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        return f"Echo: {text}"

    async def _arun(
        self, text: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        return self._run(text)
