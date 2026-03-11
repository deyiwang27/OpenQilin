"""Configuration primitives shared by runtime modules."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """Global runtime settings scaffold."""

    model_config = SettingsConfigDict(env_prefix="OPENQILIN_", extra="ignore")

    env: str = "local_dev"
    smoke_api_base_url: str = "http://127.0.0.1:8000"
    connector_shared_secret: str = "dev-openqilin-secret"
    llm_default_routing_profile: str = "dev_gemini_free"
    llm_default_quota_request_cap: int = 1_000
    llm_default_quota_token_cap: int = 100_000
    llm_default_allocation_mode: str = "hybrid"
    llm_default_project_share_ratio: float = 0.1
    llm_default_budget_window: str = "daily"
