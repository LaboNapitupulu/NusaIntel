from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Severity = Literal["info", "warning", "critical"]
ColumnType = Literal["string", "integer", "number", "boolean", "date", "datetime"]


class ColumnRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    type: ColumnType
    nullable: bool = False


class UniquenessRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: list[str] = Field(min_length=1)
    severity: Severity = "critical"


class ValueRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column: str
    minimum: float | None = None
    maximum: float | None = None
    accepted_values: list[str | int | float | bool] | None = None
    severity: Severity = "critical"

    @model_validator(mode="after")
    def validate_bounds(self) -> ValueRule:
        if self.minimum is None and self.maximum is None and not self.accepted_values:
            raise ValueError("value rule requires a bound or accepted_values")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum cannot exceed maximum")
        return self


class CustomRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(pattern=r"^[a-z][a-z0-9_]{2,127}$")
    operator: Literal["non_null_ratio_gte", "row_count_gte", "row_count_lte"]
    column: str | None = None
    threshold: float
    severity: Severity = "warning"

    @model_validator(mode="after")
    def validate_operator(self) -> CustomRule:
        if self.operator == "non_null_ratio_gte" and not self.column:
            raise ValueError("column is required for non_null_ratio_gte")
        if self.operator == "non_null_ratio_gte" and not 0 <= self.threshold <= 1:
            raise ValueError("non-null ratio threshold must be between 0 and 1")
        if self.operator.startswith("row_count") and self.threshold < 0:
            raise ValueError("row-count threshold cannot be negative")
        return self


class FreshnessRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retrieval_max_age_seconds: Annotated[int, Field(gt=0)]
    severity: Severity = "critical"


class RowCountRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maximum_change_percent: Annotated[float, Field(ge=0)]
    severity: Severity = "warning"


class DatasetContractSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    dataset_code: str = Field(min_length=1, max_length=128)
    contract_version: Annotated[int, Field(gt=0)]
    columns: list[ColumnRule] = Field(min_length=1)
    uniqueness: list[UniquenessRule] = Field(default_factory=list)
    values: list[ValueRule] = Field(default_factory=list)
    custom_checks: list[CustomRule] = Field(default_factory=list)
    freshness: FreshnessRule
    row_count: RowCountRule
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self) -> DatasetContractSchema:
        names = [column.name for column in self.columns]
        if len(names) != len(set(names)):
            raise ValueError("column names must be unique")
        known = set(names)
        referenced = {column for rule in self.uniqueness for column in rule.columns} | {
            rule.column for rule in self.values
        }
        referenced |= {rule.column for rule in self.custom_checks if rule.column is not None}
        unknown = sorted(referenced - known)
        if unknown:
            raise ValueError(f"rules reference unknown columns: {', '.join(unknown)}")
        return self


NORMALIZED_COLUMNS = [
    ColumnRule(name="observation_key", type="string"),
    ColumnRule(name="region_code", type="string"),
    ColumnRule(name="region_name", type="string"),
    ColumnRule(name="indicator_code", type="string"),
    ColumnRule(name="period", type="date"),
    ColumnRule(name="value", type="number", nullable=True),
    ColumnRule(name="source_value", type="string", nullable=True),
    ColumnRule(name="value_status", type="string"),
    ColumnRule(name="unit", type="string"),
    ColumnRule(name="is_national_aggregate", type="boolean"),
]


def build_indicator_contract(dataset_code: str, *, layer: str) -> DatasetContractSchema:
    return DatasetContractSchema(
        dataset_code=dataset_code,
        contract_version=2,
        columns=NORMALIZED_COLUMNS,
        uniqueness=[
            UniquenessRule(columns=["observation_key"]),
            UniquenessRule(columns=["region_code", "indicator_code", "period"]),
        ],
        values=[
            ValueRule(
                column="value_status",
                accepted_values=["observed", "missing", "invalid"],
            )
        ],
        custom_checks=[
            CustomRule(
                code="observed_values_present",
                operator="non_null_ratio_gte",
                column="value",
                threshold=0.5,
                severity="warning",
            )
        ],
        freshness=FreshnessRule(retrieval_max_age_seconds=32 * 24 * 60 * 60),
        row_count=RowCountRule(maximum_change_percent=50),
        metadata={"layer": layer, "owner": "Data Engineering"},
    )
