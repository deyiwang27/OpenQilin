"""Configuration primitives shared by runtime modules."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """Global runtime settings scaffold."""

    model_config = SettingsConfigDict(env_prefix="OPENQILIN_", extra="ignore")

    env: str = "local_dev"
