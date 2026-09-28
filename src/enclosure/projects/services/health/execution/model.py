from abc import ABC
from enum import StrEnum
from typing import Annotated, Literal

from modwire.application import CacheOutcome
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from ...reports.model import ArchitectureSource
from ..attestations.model import ArchitectureConformanceAttestation
from ..conformance.model import ArchitectureConformanceReport, ArchitectureHealthContract


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
    contract: ArchitectureHealthContract


class HealthExecutionResult(HealthExecutionValue, ABC):
    cache_outcomes: tuple[CacheOutcome, ...]
    detail: str


class CompletedHealthExecutionResult(HealthExecutionResult):
    outcome: Literal[HealthRunOutcome.COMPLETED] = HealthRunOutcome.COMPLETED
    healthy: bool
    reports: tuple[dict[str, JsonValue], ...]
    conformance: ArchitectureConformanceReport
    attestation: ArchitectureConformanceAttestation


class IncompleteHealthExecutionResult(HealthExecutionResult):
    outcome: Literal[
        HealthRunOutcome.CANCELED,
        HealthRunOutcome.TIMED_OUT,
        HealthRunOutcome.FAILED,
    ]


class HealthExecutionResponse(HealthExecutionValue):
    result: Annotated[
        CompletedHealthExecutionResult | IncompleteHealthExecutionResult,
        Field(discriminator="outcome"),
    ]
