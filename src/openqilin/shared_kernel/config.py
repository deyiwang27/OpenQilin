"""Configuration primitives shared by runtime modules."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass
class ConversationMemoryConfig:
    """Configuration for conversation memory tiers.

    hot_window_size: number of message rows kept verbatim (each exchange = 2 rows).
                     Default 40 = 20 exchanges.
    window_size:     number of rows per archived window before summarization.
                     Default 40 = 20 exchanges per window.
    max_warm_windows: maximum number of closed window summaries loaded per invocation.
    summary_model:   LLM routing profile used for window summarization.
    """

    hot_window_size: int = 40
    window_size: int = 40
    max_warm_windows: int = 10
    summary_model: str = "dev_gemini_free"


class RuntimeSettings(BaseSettings):
    """Global runtime settings scaffold."""

    model_config = SettingsConfigDict(env_prefix="OPENQILIN_", extra="ignore")

    env: str = "local_dev"
    system_root: str = "~/.openqilin"
    runtime_persistence_enabled: bool = False
    smoke_api_base_url: str = "http://127.0.0.1:8000"
    connector_shared_secret: str = "dev-openqilin-secret"
    llm_default_routing_profile: str = "dev_gemini_free"
    llm_default_quota_request_cap: int = 1_000
    llm_default_quota_token_cap: int = 100_000
    llm_default_max_tokens: int = 1024
    llm_default_allocation_mode: str = "hybrid"
    llm_default_project_share_ratio: float = 0.1
    llm_default_budget_window: str = "daily"
    llm_provider_backend: str = "in_memory"
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_request_timeout_seconds: float = 20.0
    gemini_max_retries: int = 2
    gemini_retry_base_delay_seconds: float = 1.0
    gemini_retry_max_delay_seconds: float = 8.0
    gemini_free_primary_model: str = "gemini-2.0-flash"
    gemini_free_fallback_model: str = "gemini-2.0-flash"
    discord_bot_token: str | None = None
    discord_multi_bot_enabled: bool = False
    discord_worker_role: str = "runtime_agent"
    discord_role_bot_tokens_file: str | None = None
    discord_role_bot_tokens_json: str = "{}"
    discord_required_role_bots_csv: str = "administrator,auditor,ceo,cwo,project_manager"
    discord_control_plane_base_url: str = "http://127.0.0.1:8000"
    discord_command_prefix: str = "/oq"
    discord_actor_role_default: str = "owner"
    discord_actor_role_map_json: str = "{}"
    discord_allowed_guild_ids_csv: str = ""
    discord_allowed_channel_ids_csv: str = ""
    discord_request_timeout_seconds: float = 20.0
    discord_response_chunk_size_chars: int = 1900
    discord_response_retry_attempts: int = 2
    discord_response_retry_base_delay_seconds: float = 0.5
    opa_url: str = (
        ""  # Empty = use InMemory client (local/test). Set to http://opa:8181 in compose.
    )
    database_url: str = (
        ""  # Empty = use InMemory repos (local/test). Set to postgresql+psycopg://... in compose.
    )
    redis_url: str = ""  # Empty = use InMemory idempotency store (local/test). Set to redis://redis:6379 in compose.
    idempotency_ttl_seconds: int = 86400  # TTL for idempotency keys in Redis (default: 24 hours).
    otlp_endpoint: str = (
        ""  # Empty = no OTel export (local/test). Set to http://otel_collector:4317 in compose.
    )
    grafana_public_url: str = (
        ""  # Empty = no dashboard URL announcement. Set to http://grafana:3000 in compose.
    )

    @property
    def system_root_path(self) -> Path:
        """Resolved filesystem root for OpenQilin runtime-generated artifacts."""

        return Path(self.system_root).expanduser().resolve()

    @property
    def runtime_state_snapshot_path(self) -> Path:
        """Snapshot path for task runtime-state persistence."""

        return self.system_root_path / "runtime" / "runtime_state.json"

    @property
    def communication_snapshot_path(self) -> Path:
        """Snapshot path for communication message/dead-letter persistence."""

        return self.system_root_path / "runtime" / "communication.json"

    @property
    def idempotency_snapshot_path(self) -> Path:
        """Snapshot path for idempotency cache persistence."""

        return self.system_root_path / "runtime" / "idempotency_cache.json"

    @property
    def identity_channel_snapshot_path(self) -> Path:
        """Snapshot path for connector identity/channel mapping persistence."""

        return self.system_root_path / "runtime" / "identity_channel_mappings.json"

    @property
    def agent_registry_snapshot_path(self) -> Path:
        """Snapshot path for institutional-agent registry persistence."""

        return self.system_root_path / "runtime" / "agent_registry.json"
