from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DecisionThresholds(BaseModel):
    """Gate policy, injectable in tests or configured via nested environment keys."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    freshness_seconds: int = Field(default=900, gt=0)
    future_skew_seconds: int = Field(default=30, ge=0)
    material_confidence: float = Field(default=0.50, gt=0, le=1)
    act_confidence: float = Field(default=0.70, gt=0, le=1)
    severe_conflict_confidence: float = Field(default=0.85, gt=0, le=1)
    equal_confidence_tolerance: float = Field(default=0.05, ge=0, le=1)

    @model_validator(mode="after")
    def check_confidence_thresholds(self) -> "DecisionThresholds":
        if self.act_confidence < self.material_confidence:
            raise ValueError("act_confidence must be at least material_confidence")
        return self


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PARALLAX_", env_nested_delimiter="__", env_file=".env",
        env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "PARALLAX API"
    database_url: str = "sqlite:///./parallax.db"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173"
    decision_gate: DecisionThresholds = Field(default_factory=DecisionThresholds)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
