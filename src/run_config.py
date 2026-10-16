"""Validated effective settings consumed by the deterministic audit stages."""
from __future__ import annotations

from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RunConfig(BaseModel):
    """Immutable, versioned snapshot of result-affecting analysis settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    input_mode: Literal["adult_income", "uploaded_predictions"] = "adult_income"
    protected_attributes: tuple[str, ...] = ()

    disparate_impact_ratio_threshold: float = Field(default=0.8, gt=0, le=1)
    min_group_size_warning: int = Field(default=20, ge=1)
    significance_level: float = Field(default=0.05, gt=0, lt=1)
    permutations: int = Field(default=1000, ge=1)
    permutation_random_state: int = 42

    isolation_forest_random_state: int = 42
    isolation_forest_n_estimators: int = Field(default=100, ge=1)
    anomaly_threshold_method: Literal["knee_point", "fixed_contamination"] = "knee_point"
    contamination_override: float | None = Field(default=None, gt=0, lt=0.5)

    @model_validator(mode="after")
    def validate_threshold_policy(self) -> RunConfig:
        if self.anomaly_threshold_method == "fixed_contamination" and self.contamination_override is None:
            raise ValueError("fixed_contamination requires contamination_override")
        if self.anomaly_threshold_method == "knee_point" and self.contamination_override is not None:
            raise ValueError("knee_point cannot have a contamination_override")
        if len(set(self.protected_attributes)) != len(self.protected_attributes):
            raise ValueError("protected_attributes must not contain duplicates")
        if any(not attribute.strip() for attribute in self.protected_attributes):
            raise ValueError("protected_attributes must contain non-empty names")
        return self

    @classmethod
    def from_project_config(
        cls,
        config: Mapping[str, Any],
        *,
        input_mode: Literal["adult_income", "uploaded_predictions"] = "adult_income",
        protected_attributes: Sequence[str] | None = None,
        contamination_override: float | None = None,
    ) -> RunConfig:
        fairness = config.get("fairness", {})
        anomaly = config.get("anomaly_detection", {})
        isolation_forest = anomaly.get("isolation_forest", anomaly)
        fixed_threshold = contamination_override is not None

        return cls(
            input_mode=input_mode,
            protected_attributes=tuple(
                config.get("protected_attributes", ())
                if protected_attributes is None
                else protected_attributes
            ),
            disparate_impact_ratio_threshold=fairness.get(
                "disparate_impact_ratio_threshold", 0.8
            ),
            min_group_size_warning=fairness.get("min_group_size_warning", 20),
            significance_level=fairness.get("significance_level", 0.05),
            permutations=fairness.get("permutations", 1000),
            permutation_random_state=fairness.get("permutation_random_state", 42),
            isolation_forest_random_state=isolation_forest.get("random_state", 42),
            isolation_forest_n_estimators=isolation_forest.get("n_estimators", 100),
            anomaly_threshold_method=(
                "fixed_contamination" if fixed_threshold else "knee_point"
            ),
            contamination_override=contamination_override,
        )

    def to_effective_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible snapshot suitable for trace/artifact storage."""
        return self.model_dump(mode="json")

    def to_project_config(self) -> dict[str, Any]:
        """Return the existing fairness-scanner config contract."""
        return {
            "protected_attributes": list(self.protected_attributes),
            "fairness": {
                "disparate_impact_ratio_threshold": self.disparate_impact_ratio_threshold,
                "min_group_size_warning": self.min_group_size_warning,
                "significance_level": self.significance_level,
                "permutations": self.permutations,
                "permutation_random_state": self.permutation_random_state,
            },
        }