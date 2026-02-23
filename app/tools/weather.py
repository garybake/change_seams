"""Weather tool — calls OpenWeatherMap free API."""
from typing import Any, Optional, Type

import httpx
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

from app.config import settings
from app.tools.base import ChangeSeamsTool, ToolContract

OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherInput(BaseModel):
    location: str = Field(description="City name, e.g. 'Dublin' or 'New York'")


class WeatherTool(ChangeSeamsTool):
    name: str = "weather"
    description: str = (
        "Get current weather for a city. Input: city name. "
        "Returns temperature and conditions."
    )
    args_schema: Type[BaseModel] = WeatherInput
    contract: ToolContract = ToolContract(
        name="weather",
        description="Current weather via OpenWeatherMap API.",
        args_schema={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name, e.g. 'Dublin' or 'New York'",
                }
            },
            "required": ["location"],
        },
        required_permissions=["external_api"],
    )

    def _run(
        self, location: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        api_key = settings.openweathermap_api_key
        if not api_key:
            return "Weather tool unavailable: OPENWEATHERMAP_API_KEY not configured."
        try:
            response = httpx.get(
                OPENWEATHERMAP_URL,
                params={"q": location, "appid": api_key, "units": "metric"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            temp = data["main"]["temp"]
            description = data["weather"][0]["description"]
            city = data["name"]
            country = data["sys"]["country"]
            return f"{city}, {country}: {temp:.1f}°C, {description}"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"City not found: {location!r}"
            return f"Weather API error: {e.response.status_code}"
        except Exception as e:
            return f"Weather lookup failed: {e}"

    async def _arun(
        self, location: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        api_key = settings.openweathermap_api_key
        if not api_key:
            return "Weather tool unavailable: OPENWEATHERMAP_API_KEY not configured."
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    OPENWEATHERMAP_URL,
                    params={"q": location, "appid": api_key, "units": "metric"},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                temp = data["main"]["temp"]
                description = data["weather"][0]["description"]
                city = data["name"]
                country = data["sys"]["country"]
                return f"{city}, {country}: {temp:.1f}°C, {description}"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"City not found: {location!r}"
            return f"Weather API error: {e.response.status_code}"
        except Exception as e:
            return f"Weather lookup failed: {e}"
