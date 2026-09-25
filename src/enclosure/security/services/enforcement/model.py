from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ...errors import SecurityApprovalRequiredError, SecurityAuthorizationError


class AuthorizationDecisionKind(StrEnum):
    AUTHORIZED = "authorized"
    DENIED = "denied"
    APPROVAL_REQUIRED = "approval_required"


class AuthorizationDecision(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    reason_code: str

    @property
    @abstractmethod
    def kind(self) -> AuthorizationDecisionKind:
        raise NotImplementedError

    @abstractmethod
    def enforce(self) -> None:
        raise NotImplementedError


class AuthorizedExecution(AuthorizationDecision):
    @property
    def kind(self) -> AuthorizationDecisionKind:
        return AuthorizationDecisionKind.AUTHORIZED

    def enforce(self) -> None:
        return


class DeniedAuthorization(AuthorizationDecision):
    @property
    def kind(self) -> AuthorizationDecisionKind:
        return AuthorizationDecisionKind.DENIED

    def enforce(self) -> None:
        raise SecurityAuthorizationError(self.execution_id, self.reason_code)


class ApprovalRequiredAuthorization(AuthorizationDecision):
    approval_request_id: str
    expires_at: datetime

    @property
    def kind(self) -> AuthorizationDecisionKind:
        return AuthorizationDecisionKind.APPROVAL_REQUIRED

    def enforce(self) -> None:
        raise SecurityApprovalRequiredError(
            execution_id=self.execution_id,
            reason_code=self.reason_code,
            approval_request_id=self.approval_request_id,
            expires_at=self.expires_at,
        )
