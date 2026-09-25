from collections.abc import Callable
from dataclasses import dataclass

from django.http import HttpRequest, HttpResponse
from modwire_hex.django import DjangoRequest

from ...services.audit import ExecutionOutcome
from ...services.facade import SecurityService
from ...services.policies import OperationIntent
from .authentication import DjangoActorAuthenticator


@dataclass(frozen=True)
class SecurityOutcomeMiddleware:
    get_response: Callable[[HttpRequest], HttpResponse]

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            response = self.get_response(request)
        except BaseException:
            self.record(request, ExecutionOutcome.INTERRUPTED)
            raise
        if DjangoActorAuthenticator.ACTOR_CONTEXT_KEY not in request.META:
            return response
        outcome = ExecutionOutcome.SUCCEEDED if response.status_code < 400 else ExecutionOutcome.FAILED
        self.record(request, outcome)
        return response

    def record(self, request: HttpRequest, outcome: ExecutionOutcome) -> None:
        if DjangoActorAuthenticator.ACTOR_CONTEXT_KEY not in request.META:
            return
        authenticator = DjangoRequest.resolve(request, DjangoActorAuthenticator)
        actor = authenticator.bound_actor(request)
        intent = OperationIntent.model_validate_json(request.META[DjangoActorAuthenticator.INTENT_CONTEXT_KEY])
        DjangoRequest.resolve(request, SecurityService).record_outcome(actor, intent, outcome)
