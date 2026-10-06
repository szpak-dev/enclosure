from abc import ABC
from enum import StrEnum
from typing import Annotated, Literal

from modwire.application import CacheOutcome
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from ...reports.model import ArchitectureSource
from ..attestations.model import ArchitectureConformanceAttestation
from ..conformance.model import (
    ArchitectureConformanceReport,
    ArchitectureHealthContract,
    ArchitectureHealthInputIdentity,
)


class HealthExecutionValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HealthRunOutcome(StrEnum):
    COMPLETED = "completed"
    CANCELED = "canceled"
    TIMED_OUT = "timed-out"
    REJECTED = "rejected"
    FAILED = "failed"


class HealthWorkerReadiness(StrEnum):
    READY = "ready"
    TIMED_OUT = "timed-out"
    FAILED = "failed"


class CacheOutcomeState(StrEnum):
    NOT_APPLICABLE = "not-applicable"
    HIT = "hit"
    MISS = "miss"
    STALE = "stale"
    CORRUPT = "corrupt"
    STORED = "stored"
    UNAVAILABLE = "unavailable"


class HealthCacheStage(StrEnum):
    IMPLEMENTATION_DOCUMENT = "implementation-document"
    MODWIRE_REPORTS = "modwire-reports"
    IMPLEMENTATION_EVIDENCE = "implementation-evidence"
    REALIZATION = "realization"
    COMPARISON = "comparison"
    ATTESTATION = "attestation"
    COMPLETED_RESULT = "completed-result"


class HealthCacheComponent(HealthExecutionValue):
    name: str
    digest: str


class HealthCacheIdentity(HealthExecutionValue):
    stage: HealthCacheStage
    digest: str


class HealthCacheEnvelope(HealthExecutionValue):
    schema_version: int
    stage: HealthCacheStage
    identity_digest: str
    payload_digest: str
    encoded_payload: str


class HealthCacheLookup(HealthExecutionValue):
    state: CacheOutcomeState
    payload: bytes = b""
    detail: str = ""


class HealthExecutionPhase(StrEnum):
    WORKER_BOOTSTRAP = "worker-bootstrap"
    SOURCE_INVENTORY = "source-inventory"
    MODWIRE_CODE_MAP = "modwire-code-map"
    MODWIRE_REPORTS = "modwire-reports"
    IMPLEMENTATION_MANIFEST = "implementation-manifest"
    ARTIFACT_INVENTORY = "artifact-inventory"
    EVIDENCE = "evidence"
    REALIZATION = "realization"
    COMPARISON = "comparison"
    ATTESTATION = "attestation"
    COMPLETED_RESULT_CACHE = "completed-result-cache"
    FINAL_INPUT_VERIFICATION = "final-input-verification"
    CACHE_PERSISTENCE = "cache-persistence"


class HealthPhaseToken(HealthExecutionValue):
    kind: Literal["phase-started"] = "phase-started"
    phase: HealthExecutionPhase
    started_ns: int


class HealthPhaseDiagnostic(HealthExecutionValue):
    kind: Literal["phase-diagnostic"] = "phase-diagnostic"
    phase: HealthExecutionPhase
    duration_ns: int
    outcome: str
    item_count: int = 0
    cache_outcome: CacheOutcomeState = CacheOutcomeState.NOT_APPLICABLE
    cache_stages: tuple[HealthCacheStage, ...] = ()


class HealthWorkerReady(HealthExecutionValue):
    kind: Literal["worker-ready"] = "worker-ready"


class HealthCacheOutcomeDiagnostic(HealthExecutionValue):
    kind: Literal["cache-outcomes"] = "cache-outcomes"
    outcomes: tuple[CacheOutcome, ...]


class HealthExecutionRequest(HealthExecutionValue):
    run_id: str
    source: ArchitectureSource
    contract: ArchitectureHealthContract


class HealthExecutionResult(HealthExecutionValue, ABC):
    cache_outcomes: tuple[CacheOutcome, ...]
    phase_diagnostics: tuple[HealthPhaseDiagnostic, ...]
    detail: str


class CompletedHealthExecutionResult(HealthExecutionResult):
    outcome: Literal[HealthRunOutcome.COMPLETED] = HealthRunOutcome.COMPLETED
    healthy: bool
    reports: tuple[dict[str, JsonValue], ...]
    conformance: ArchitectureConformanceReport
    attestation: ArchitectureConformanceAttestation
    input_identity: ArchitectureHealthInputIdentity


class IncompleteHealthExecutionResult(HealthExecutionResult):
    outcome: Literal[
        HealthRunOutcome.CANCELED,
        HealthRunOutcome.TIMED_OUT,
        HealthRunOutcome.REJECTED,
        HealthRunOutcome.FAILED,
    ]


class HealthExecutionResponse(HealthExecutionValue):
    kind: Literal["result"] = "result"
    result: Annotated[
        CompletedHealthExecutionResult | IncompleteHealthExecutionResult,
        Field(discriminator="outcome"),
    ]


class HealthWorkerMessage(HealthExecutionValue):
    message: Annotated[
        HealthPhaseToken | HealthPhaseDiagnostic | HealthCacheOutcomeDiagnostic | HealthExecutionResponse,
        Field(discriminator="kind"),
    ]
