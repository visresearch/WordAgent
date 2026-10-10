"""Validated per-model generation parameters shared by settings and inference."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelParameters(BaseModel):
    temperature: float = Field(default=0.5, ge=0, le=2, allow_inf_nan=False)
    # Keep the existing frontend/API field names.
    topP: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)  # noqa: N815
    maxTokens: int = Field(default=8192, ge=1, le=2**53 - 1, strict=True)  # noqa: N815
    reasoningEffort: Literal["none", "minimal", "low", "medium", "high", "xhigh"] = "medium"  # noqa: N815

    @field_validator("maxTokens", "reasoningEffort", mode="before")
    @classmethod
    def fill_legacy_defaults(cls, value, info):
        if value is None or value == "":
            return 8192 if info.field_name == "maxTokens" else "medium"
        return value


class ModelConfig(BaseModel):
    # Preserve provider metadata, while removed/unknown generation parameters are discarded.
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    name: str | None = None
    enabled: bool = False
    parameters: ModelParameters = Field(default_factory=ModelParameters)

    @field_validator("parameters", mode="before")
    @classmethod
    def fill_missing_parameters(cls, value):
        return {} if value is None else value
