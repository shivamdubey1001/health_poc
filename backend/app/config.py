from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Humana Ahead API"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./humana_ahead.db"
    data_dir: str = "../data"
    frontend_origin: str = "http://localhost:5173"

    # Real OpenAI mode is the default. The API key stays server-side only.
    use_mock_ai: bool = False
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-terra"

    care_intent_threshold: float = 0.70
    recent_call_limit: int = 6
    claim_lookback_months: int = 12
    enable_transcript_fallback: bool = True
    max_scan_batch: int = 25

    # Used only to estimate session inference spend from API-reported token usage.
    # Defaults match the configured model at the time this prototype was built.
    input_cost_per_m_tokens: float = 2.00
    output_cost_per_m_tokens: float = 12.00

    data_as_of: str = "2026-08-29"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def data_path(self) -> Path:
        return (Path(__file__).resolve().parent.parent / self.data_dir).resolve()


settings = Settings()
