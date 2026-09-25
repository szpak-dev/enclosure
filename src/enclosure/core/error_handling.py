from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse

from ..security.errors import (
    ApprovalResolutionError,
    SecurityApprovalRequiredError,
    SecurityAuthenticationError,
    SecurityAuthorizationError,
    UnmappedOperationError,
)
from .errors import DomainError, GatewayTimeoutError, InternalExecutionError, ServiceUnavailableError


class ExceptionHandlers:
    def configure(self, api: Any) -> None:
        api.add_exception_handler(ObjectDoesNotExist, self.not_found_response)
        api.add_exception_handler(ServiceUnavailableError, self.service_unavailable_response)
        api.add_exception_handler(GatewayTimeoutError, self.gateway_timeout_response)
        api.add_exception_handler(InternalExecutionError, self.internal_execution_response)
        api.add_exception_handler(SecurityAuthenticationError, self.authentication_response)
        api.add_exception_handler(SecurityAuthorizationError, self.authorization_response)
        api.add_exception_handler(SecurityApprovalRequiredError, self.approval_required_response)
        api.add_exception_handler(ApprovalResolutionError, self.approval_resolution_response)
        api.add_exception_handler(UnmappedOperationError, self.unmapped_operation_response)
        api.add_exception_handler(DomainError, self.domain_error_response)
        api.add_exception_handler(Exception, self.unexpected_error_response)

    def not_found_response(self, request: HttpRequest, error: ObjectDoesNotExist) -> HttpResponse:
        return self.response(request, {"detail": "Resource not found."}, status=404)

    def domain_error_response(self, request: HttpRequest, error: DomainError) -> HttpResponse:
        return self.response(request, {"detail": str(error)}, status=422)

    def service_unavailable_response(self, request: HttpRequest, error: ServiceUnavailableError) -> HttpResponse:
        return self.response(request, {"detail": str(error)}, status=503)

    def gateway_timeout_response(self, request: HttpRequest, error: GatewayTimeoutError) -> HttpResponse:
        return self.response(request, {"detail": str(error)}, status=504)

    def internal_execution_response(self, request: HttpRequest, error: InternalExecutionError) -> HttpResponse:
        return self.response(request, {"detail": str(error)}, status=500)

    def authentication_response(self, request: HttpRequest, error: SecurityAuthenticationError) -> HttpResponse:
        return self.response(request, {"detail": str(error), "reason_code": error.reason_code}, status=401)

    def authorization_response(self, request: HttpRequest, error: SecurityAuthorizationError) -> HttpResponse:
        return self.response(
            request,
            {"detail": str(error), "execution_id": error.execution_id, "reason_code": error.reason_code},
            status=403,
        )

    def approval_required_response(
        self,
        request: HttpRequest,
        error: SecurityApprovalRequiredError,
    ) -> HttpResponse:
        return self.response(
            request,
            {
                "detail": str(error),
                "execution_id": error.execution_id,
                "reason_code": error.reason_code,
                "approval_request_id": error.approval_request_id,
                "expires_at": error.expires_at.isoformat(),
            },
            status=409,
        )

    def approval_resolution_response(self, request: HttpRequest, error: ApprovalResolutionError) -> HttpResponse:
        return self.response(request, {"detail": str(error)}, status=409)

    def unmapped_operation_response(self, request: HttpRequest, error: UnmappedOperationError) -> HttpResponse:
        return self.response(
            request,
            {"detail": "The operation has no authorization policy.", "reason_code": "operation_unmapped"},
            status=500,
        )

    def unexpected_error_response(self, request: HttpRequest, error: Exception) -> HttpResponse:
        return self.response(request, {"detail": str(error)}, status=500)

    def response(self, request: HttpRequest, payload: dict[str, Any], status: int) -> HttpResponse:
        from modwire_hex.django import DjangoNinja

        return DjangoNinja.api().create_response(request, payload, status=status)
