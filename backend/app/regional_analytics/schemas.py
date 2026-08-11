from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeatureSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indicator_codes: list[str] = Field(min_length=2, max_length=6)
    year: int = Field(ge=2000, le=2100)
    minimum_feature_coverage: Decimal = Field(default=Decimal("0.95"), gt=0, le=1)

    @field_validator("indicator_codes")
    @classmethod
    def indicators_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Indicator codes must be unique")
        return value


class SimilarityRequest(FeatureSetRequest):
    target_region_code: str = Field(min_length=4, max_length=16)
    limit: int = Field(default=5, ge=1, le=10)


class ClusterRequest(FeatureSetRequest):
    candidate_k: list[int] = Field(default_factory=lambda: [2, 3, 4, 5], min_length=1, max_length=5)
    seeds: list[int] = Field(default_factory=lambda: [11, 29, 47], min_length=2, max_length=10)
    minimum_silhouette: Decimal = Field(default=Decimal("0.10"), ge=-1, le=1)
    minimum_stability: Decimal = Field(default=Decimal("0.60"), ge=0, le=1)

    @field_validator("candidate_k", "seeds")
    @classmethod
    def integer_values_must_be_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Values must be unique")
        return value


class AnalyticsReportRequest(SimilarityRequest):
    candidate_k: list[int] = Field(default_factory=lambda: [2, 3, 4, 5], min_length=1, max_length=5)
    seeds: list[int] = Field(default_factory=lambda: [11, 29, 47], min_length=2, max_length=10)
    minimum_silhouette: Decimal = Field(default=Decimal("0.10"), ge=-1, le=1)
    minimum_stability: Decimal = Field(default=Decimal("0.60"), ge=0, le=1)

    @field_validator("candidate_k", "seeds")
    @classmethod
    def report_integer_values_must_be_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Values must be unique")
        return value
