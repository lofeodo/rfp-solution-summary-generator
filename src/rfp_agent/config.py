"""Configuration: one settings object read from the environment and ``.env``.

Provider and model are a single setting written ``<provider>:<model_id>``, e.g.
``deepseek:deepseek-flash`` or ``anthropic:claude-sonnet-5-5``. Any provider LangChain's
``init_chat_model`` knows works, so swapping models is an environment-variable change.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# --------------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"
INPUTS_DIR = REPO_ROOT / "inputs"
DATA_DIR = REPO_ROOT / "data"
RUNS_DIR = REPO_ROOT / "runs"
DEFAULT_INPUT = INPUTS_DIR / "rfp_brief.pdf"


# --------------------------------------------------------------------------------------
# Model spec helpers
# --------------------------------------------------------------------------------------


def split_model_spec(spec: str) -> tuple[str, str]:
    """Split ``"provider:model_id"`` into ``("provider", "model_id")``.

    Raises ``ValueError`` when the provider prefix is missing, so a misconfigured
    environment fails at startup rather than at the first LLM call.
    """
    provider, sep, model_id = spec.partition(":")
    if not sep or not provider.strip() or not model_id.strip():
        raise ValueError(
            f"Model spec {spec!r} must look like '<provider>:<model_id>', "
            "e.g. 'deepseek:deepseek-flash'"
        )
    return provider.strip().lower(), model_id.strip()


# --------------------------------------------------------------------------------------
# Pricing table (USD per 1M tokens). S1 does the arithmetic; this is the lookup.
# --------------------------------------------------------------------------------------


class ModelPricing(BaseModel):
    input_per_mtok: float = Field(ge=0)
    cached_input_per_mtok: float = Field(ge=0)
    output_per_mtok: float = Field(ge=0)


# Sources, checked 2026-10-30:
# - DeepSeek: https://api-docs.deepseek.com/quick_start/pricing. Peak rates are used as
#   the upper bound; off-peak (outside 01:00-04:00 and 06:00-10:00 UTC on weekdays) is
#   half of every number below.
# - Anthropic: first-party API rates.
PRICING: dict[str, ModelPricing] = {
    "deepseek-flash": ModelPricing(
        input_per_mtok=0.30, cached_input_per_mtok=0.006, output_per_mtok=1.20
    ),
    "deepseek-v4-pro": ModelPricing(
        input_per_mtok=1.32, cached_input_per_mtok=0.044, output_per_mtok=3.96
    ),
    "claude-opus-5-5": ModelPricing(
        input_per_mtok=4.00, cached_input_per_mtok=0.20, output_per_mtok=20.00
    ),
    "claude-sonnet-5-5": ModelPricing(
        input_per_mtok=2.00, cached_input_per_mtok=0.20, output_per_mtok=10.00
    ),
    "claude-haiku-5-5": ModelPricing(
        input_per_mtok=0.10, cached_input_per_mtok=0.01, output_per_mtok=0.50
    ),
}


def pricing_for(model: str) -> ModelPricing | None:
    """Look up pricing by bare model id or full ``provider:model_id`` spec.

    Returns ``None`` for unknown models so the caller can record cost as unknown rather
    than guess.
    """
    model_id = model.partition(":")[2] if ":" in model else model
    return PRICING.get(model_id)


# --------------------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------------------


class Settings(BaseSettings):
    """Runtime settings. ``RFP_*`` variables override the defaults; keys use their
    providers' conventional names."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="RFP_",
        extra="ignore",
    )

    # Models
    model: str = "deepseek:deepseek-flash"
    judge_model: str = "anthropic:claude-sonnet-5-5"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_structured_retries: int = Field(
        default=2, ge=0, description="Retries after a schema validation failure"
    )
    max_output_tokens: int | None = Field(
        default=None, ge=1, description="Output cap per call; None uses the provider default"
    )
    request_timeout_s: float = Field(default=120.0, gt=0, description="Per-request timeout")
    llm_transport_retries: int = Field(
        default=2, ge=0, description="SDK-level retries on 429/5xx/connection errors"
    )
    deepseek_thinking: bool = Field(
        default=False,
        description="DeepSeek thinking mode. Off: forced tool calling for structured output. "
        "On: JSON mode (thinking mode rejects forced tool_choice).",
    )
    llm_concurrency: int = Field(
        default=4,
        ge=1,
        description="Parallel LLM calls in per-chunk stages (S6 chunk summaries)",
    )

    # Ablation flags (S10 CLI exposes them; S6 and S5 read them)
    full_text_problem: bool = Field(
        default=False, description="Problem statement from one full-text call"
    )
    single_call_extraction: bool = Field(
        default=False, description="Requirements from one full-document call"
    )

    # Provider keys (no RFP_ prefix: these are the names the SDKs expect)
    deepseek_api_key: str | None = Field(default=None, validation_alias="DEEPSEEK_API_KEY")
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    # Langfuse (optional)
    langfuse_public_key: str | None = Field(default=None, validation_alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = Field(default=None, validation_alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", validation_alias="LANGFUSE_HOST"
    )

    @property
    def generator(self) -> tuple[str, str]:
        return split_model_spec(self.model)

    @property
    def judge(self) -> tuple[str, str]:
        return split_model_spec(self.judge_model)

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings. Tests call ``get_settings.cache_clear()``."""
    return Settings()
