from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Impact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: float = Field(default=0, ge=0, allow_inf_nan=False)
    currency: str = Field(default="INR", min_length=3, max_length=3)


class PolicyRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: str = Field(min_length=3, max_length=100)
    target: str | None = Field(default=None, max_length=200)
    effect: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
    min_risk: int | None = Field(default=None, ge=0, le=100)
    reason_code: str = Field(default="POLICY_RULE_MATCHED", min_length=2, max_length=80)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=3, max_length=100)
    target: str = Field(min_length=3, max_length=200)
    parameters: dict[str, Any] = Field(default_factory=dict)
    environment: Literal["development", "staging", "production"]
    data_classification: Literal["public", "internal", "confidential", "restricted"]
    impact: Impact = Field(default_factory=Impact)

    @field_validator("parameters")
    @classmethod
    def limit_parameters(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(str(value)) > 8000:
            raise ValueError("Action parameters exceed the 8 KB demo limit")
        return value


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: UUID
    action: Action


class PolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=120)
    rules: list[PolicyRule] = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Policy name must have at least two non-space characters")
        return normalized


class AgentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Agent name must have at least two non-space characters")
        return normalized


class ApprovalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rationale: str = Field(min_length=3, max_length=500)
