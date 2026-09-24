from enum import StrEnum

from modwire.application import CacheOutcome
from pydantic import BaseModel, ConfigDict, JsonValue

from ...reports.model import ArchitectureSource


class HealthExecutionValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HealthRunOutcome(StrEnum):
    COMPLETED = "completed"
    CANCELED = "canceled"
    TIMED_OUT = "timed-out"
    FAILED = "failed"


class HealthExecutionRequest(HealthExecutionValue):
    run_id: str
    source: ArchitectureSource


class HealthExecutionResult(HealthExecutionValue):
    outcome: HealthRunOutcome
    reports: tuple[dict[str, JsonValue], ...]
    cache_outcomes: tuple[CacheOutcome, ...]
    detail: str
