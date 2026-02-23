from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Provider (Seam 1)
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    tavily_api_key: str = ""
    openweathermap_api_key: str = ""

    # Tool Enablement (Seam 3) — stored as a raw comma-separated string so
    # pydantic-settings doesn't attempt JSON parsing on the env value.
    # Use the `enabled_tools` property to get the parsed list.
    enabled_tools_csv: str = Field("echo", alias="ENABLED_TOOLS")

    # Policy Mode (Seam 4)
    policy_mode: str = "default"

    # Database
    database_url: str = "postgresql+asyncpg://change_seams:change_seams@localhost:5432/change_seams"

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def enabled_tools(self) -> list[str]:
        return [t.strip() for t in self.enabled_tools_csv.split(",") if t.strip()]


settings = Settings()
