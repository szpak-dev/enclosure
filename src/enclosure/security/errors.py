from datetime import datetime


class SecurityAuthenticationError(Exception):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__("Authentication is required.")


class SecurityAuthorizationError(Exception):
    def __init__(self, execution_id: str, reason_code: str) -> None:
        self.execution_id = execution_id
        self.reason_code = reason_code
        super().__init__("The actor is not authorized for this operation.")


class SecurityApprovalRequiredError(Exception):
    def __init__(
        self,
        execution_id: str,
        reason_code: str,
        approval_request_id: str,
        expires_at: datetime,
    ) -> None:
        self.execution_id = execution_id
        self.reason_code = reason_code
        self.approval_request_id = approval_request_id
        self.expires_at = expires_at
        super().__init__("This operation requires an approved one-time request.")


class UnmappedOperationError(Exception):
    def __init__(self, method: str, route: str) -> None:
        self.method = method
        self.route = route
        super().__init__(f"Operation policy is not defined for {method} {route}.")


class ApprovalResolutionError(Exception):
    """An approval request cannot transition to the requested resolution."""
