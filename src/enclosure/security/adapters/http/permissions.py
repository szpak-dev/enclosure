from dataclasses import dataclass
from uuid import uuid7

from django.http import HttpRequest
from modwire_hex.django import DjangoRequest
from ninja_extra.controllers import ControllerBase
from ninja_extra.permissions import BasePermission

from ...errors import UnmappedOperationError
from ...services.enforcement.service import OperationIntentFactory
from ...services.facade import SecurityService
from ...services.policies.model import OperationClassification
from ...services.policies.registry import OperationPolicyRegistry
from .authentication import DjangoActorAuthenticator


@dataclass(frozen=True)
class SecurityPermission(BasePermission):
    def has_permission(self, request: HttpRequest, controller: ControllerBase) -> bool:
        authenticator = DjangoRequest.resolve(request, DjangoActorAuthenticator)
        actor = authenticator.authenticate(request)
        route = self.route(request)
        registry = DjangoRequest.resolve(request, OperationPolicyRegistry)
        policy = registry.policy(
            method=request.method,
            route=route,
            classification=self.classification(request, registry),
        )
        intent = DjangoRequest.resolve(request, OperationIntentFactory).create(
            policy=policy,
            target=self.target(request, route),
            payload=request.body + b"\x00" + request.META["QUERY_STRING"].encode(),
            correlation_id=str(uuid7()),
        )
        decision = DjangoRequest.resolve(request, SecurityService).authorize(actor, intent)
        decision.enforce()
        authenticator.bind(request, actor, intent.model_dump_json())
        return True

    def route(self, request: HttpRequest) -> str:
        resolver_match = request.resolver_match
        if resolver_match is None or resolver_match.route is None:
            raise UnmappedOperationError(request.method, request.path)
        return resolver_match.route

    def classification(
        self,
        request: HttpRequest,
        registry: OperationPolicyRegistry,
    ) -> OperationClassification:
        return registry.classification(request.method)

    def target(self, request: HttpRequest, route: str) -> str:
        resolver_match = request.resolver_match
        if resolver_match is None:
            raise UnmappedOperationError(request.method, request.path)
        parameters = "&".join(f"{name}={value}" for name, value in sorted(resolver_match.kwargs.items()))
        return route if not parameters else f"{route}?{parameters}"


class ApprovalPermission(SecurityPermission):
    def classification(
        self,
        request: HttpRequest,
        registry: OperationPolicyRegistry,
    ) -> OperationClassification:
        return OperationClassification.APPROVAL


class AuditPermission(SecurityPermission):
    def classification(
        self,
        request: HttpRequest,
        registry: OperationPolicyRegistry,
    ) -> OperationClassification:
        return OperationClassification.AUDIT


class ReadSecurityPermission(SecurityPermission):
    def classification(
        self,
        request: HttpRequest,
        registry: OperationPolicyRegistry,
    ) -> OperationClassification:
        return OperationClassification.READ
