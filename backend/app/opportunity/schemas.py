from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeightedIndicatorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=128)
    weight: Decimal = Field(ge=0, le=100)
    direction: Literal["higher", "lower"]


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_codes: list[str] = Field(min_length=2, max_length=5)
    indicator_codes: list[str] = Field(min_length=1, max_length=6)
    year: int = Field(ge=2000, le=2100)
    normalization: Literal["min_max", "percentile"] = "min_max"

    @field_validator("region_codes", "indicator_codes")
    @classmethod
    def values_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Values must be unique")
        return value


class ScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_codes: list[str] = Field(min_length=2, max_length=5)
    indicators: list[WeightedIndicatorRequest] = Field(min_length=1, max_length=6)
    year: int = Field(ge=2000, le=2100)
    normalization: Literal["min_max", "percentile"] = "min_max"
    coverage_threshold: Decimal = Field(default=Decimal(1), ge=0, le=1)

    @field_validator("region_codes")
    @classmethod
    def regions_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Region codes must be unique")
        return value


class SensitivityRequest(ScoreRequest):
    perturbation: Decimal = Field(default=Decimal("0.10"), gt=0, le=Decimal("0.50"))
