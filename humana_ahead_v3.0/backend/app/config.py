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

    # Determinism. Administrative gating decisions must be reproducible, and an
    # evaluation number is meaningless if the same input yields different output.
    openai_temperature: float = 0.0
    openai_timeout_seconds: int = 90
    openai_max_retries: int = 3

    # Bumped whenever a system prompt changes, and stored with every result so a
    # past prediction can be tied to the exact instructions that produced it.
    prompt_version: str = "2026-08-30.v2"

    care_intent_threshold: float = 0.70
    recent_call_limit: int = 6
    claim_lookback_months: int = 12
    enable_transcript_fallback: bool = True
    max_scan_batch: int = 25

    # Concurrency for batch scans. Small enough to stay inside provider rate
    # limits, large enough that a 25-member scan is not a two-minute wait.
    scan_concurrency: int = 5

    # Evaluation. Held-out labels are derived from prior-authorization records,
    # which Agent 1 is explicitly forbidden from seeing.
    eval_horizon_days: int = 90

    # Used only to estimate session inference spend from API-reported token usage.
    input_cost_per_m_tokens: float = 2.00
    output_cost_per_m_tokens: float = 12.00

    data_as_of: str = "2026-08-29"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def data_path(self) -> Path:
        return (Path(__file__).resolve().parent.parent / self.data_dir).resolve()


settings = Settings()
