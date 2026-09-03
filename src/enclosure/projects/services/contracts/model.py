from typing import Literal

from pydantic import BaseModel, ConfigDict


class OperatingContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    authority: str
    provenance: str


class OperatingContractReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["guidance", "policy", "architecture"]
    id: str
    authority: str
    revision: str


class OperatingContractRevision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    contract_id: str
    version: int
    references: tuple[OperatingContractReference, ...]


class ConfiguredOperatingContractBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["configured"] = "configured"
    project_id: str
    contract: OperatingContract
    update_policy: Literal["pinned", "follow-latest"]
    bound_revision: int
    effective_revision: OperatingContractRevision


class UnconfiguredOperatingContractBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["unconfigured"] = "unconfigured"
    project_id: str
