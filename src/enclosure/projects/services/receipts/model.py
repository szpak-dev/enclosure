from typing import Literal

from pydantic import BaseModel, ConfigDict


class WorkspaceAuthority(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["project-operating-contract"]
    id: str
    revision: str
    provenance: str


class WorkspaceContextDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str
    guidance_ids: tuple[str, ...]


class ReceiptItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str
    title: str
    requirement: Literal["mandatory", "supplemental"]
    reason: Literal["operating-contract", "task-applicable", "project-default"]
    explanation: str
    authority: str
    revision: str
    checks: tuple[str, ...]


class ContextBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    used_optional_characters: int
    optional_character_limit: int


class ContextCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["complete", "partial"]
    selected_count: int
    omitted_count: int
    diagnostic_count: int


class ContextOmission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: Literal["optional-budget-exhausted"]
    guidance_ids: tuple[str, ...]
    message: str


class ContextReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    authority: WorkspaceAuthority
    items: tuple[ReceiptItem, ...]
    required_checks: tuple[str, ...]
    budget: ContextBudget
    coverage: ContextCoverage
    omissions: tuple[ContextOmission, ...]
    diagnostics: tuple[WorkspaceContextDiagnostic, ...]
    stop_condition: Literal["selected-guidance-and-checks", "resolve-context-gaps"]
