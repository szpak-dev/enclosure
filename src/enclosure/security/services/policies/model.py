from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class OperationClassification(StrEnum):
    READ = "read"
    MUTATION = "mutation"
    DESTRUCTIVE = "destructive"
    APPROVAL = "approval"
    AUDIT = "audit"


class OperationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    method: str
    route: str
    operation_id: str
    classification: OperationClassification
    required_permission: str


class OperationIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    operation_id: str
    classification: OperationClassification
    method: str
    route: str
    target: str
    payload_digest: str
    correlation_id: str
    required_permission: str
