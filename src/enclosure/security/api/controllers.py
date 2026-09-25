from typing import Annotated

from django.http import HttpRequest
from modwire_hex.django import DjangoRequest
from ninja import Path, Query
from ninja_extra import ControllerBase, api_controller, route

from ..adapters.http import ApprovalPermission, AuditPermission, DjangoActorAuthenticator
from ..services.facade import SecurityService
from . import schemas


@api_controller(
    "/security/approval-requests",
    tags=["Security approvals"],
    permissions=[ApprovalPermission],
)
class ApprovalController(ControllerBase):
    @route.get(
        "/{approval_request_id}",
        response=schemas.ApprovalRequest,
        operation_id="get_approval_request",
        summary="Get an approval request",
        description="Return the exact actor, operation, target, payload digest, expiry, and current resolution state.",
    )
    def get(
        self,
        request: HttpRequest,
        approval_request_id: Annotated[str, Path(description="Approval request identifier.")],
    ):
        return DjangoRequest.resolve(request, SecurityService).get_approval(approval_request_id)

    @route.post(
        "/{approval_request_id}/approvals",
        response=schemas.ApprovalRequest,
        operation_id="approve_operation",
        summary="Approve an operation once",
        description="Approve one exact pending destructive operation for one-time consumption before expiry.",
    )
    def approve(
        self,
        request: HttpRequest,
        approval_request_id: Annotated[str, Path(description="Approval request identifier.")],
    ):
        return DjangoRequest.resolve(request, SecurityService).approve(
            approval_request_id,
            DjangoRequest.resolve(request, DjangoActorAuthenticator).bound_actor(request),
        )

    @route.post(
        "/{approval_request_id}/rejections",
        response=schemas.ApprovalRequest,
        operation_id="reject_operation",
        summary="Reject an operation",
        description="Reject one exact pending destructive operation before expiry.",
    )
    def reject(
        self,
        request: HttpRequest,
        approval_request_id: Annotated[str, Path(description="Approval request identifier.")],
    ):
        return DjangoRequest.resolve(request, SecurityService).reject(
            approval_request_id,
            DjangoRequest.resolve(request, DjangoActorAuthenticator).bound_actor(request),
        )


@api_controller(
    "/security/audit-events",
    tags=["Security audit"],
    permissions=[AuditPermission],
)
class AuditController(ControllerBase):
    @route.get(
        "",
        response=schemas.AuditEventPage,
        operation_id="find_audit_events",
        summary="List security audit events",
        description="Return a bounded page of immutable authorization and execution audit events.",
    )
    def find(self, request: HttpRequest, query: Query[schemas.FindAuditEvents]):
        return DjangoRequest.resolve(request, SecurityService).find_audit_events(query.offset, query.limit)
