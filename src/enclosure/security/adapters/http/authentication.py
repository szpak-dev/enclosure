from dataclasses import dataclass
from typing import ClassVar

from django.conf import settings
from django.http import HttpRequest
from wireup import injectable

from ...errors import SecurityAuthenticationError
from ...services.actors import (
    Actor,
    ActorKind,
    AuthenticationMethod,
    BearerIdentityProvider,
)
from ...services.actors.errors import InvalidBearerTokenError


@injectable
@dataclass(frozen=True)
class DjangoActorAuthenticator:
    ACTOR_CONTEXT_KEY: ClassVar[str] = "enclosure.actor"
    INTENT_CONTEXT_KEY: ClassVar[str] = "enclosure.intent"
    INTERNAL_ACTOR_HEADER: ClassVar[str] = "X-Enclosure-Actor-Envelope"

    bearer: BearerIdentityProvider

    def authenticate(self, request: HttpRequest) -> Actor:
        if self.INTERNAL_ACTOR_HEADER in request.headers:
            return self.internal_actor(request.headers[self.INTERNAL_ACTOR_HEADER])
        if request.user.is_authenticated:
            session_id = request.session.session_key if request.session.session_key is not None else "authenticated"
            permissions = ("*",) if request.user.is_superuser else tuple(sorted(request.user.get_all_permissions()))
            return Actor(
                id=str(request.user.pk),
                kind=ActorKind.HUMAN,
                authentication_method=AuthenticationMethod.SESSION,
                permissions=permissions,
                session_id=session_id,
            )
        if "Authorization" in request.headers:
            authorization = request.headers["Authorization"]
            if authorization.startswith("Bearer "):
                try:
                    return self.bearer.authenticate(authorization.removeprefix("Bearer "))
                except InvalidBearerTokenError as error:
                    raise SecurityAuthenticationError("invalid_bearer_token") from error
        if settings.LOCAL_DEVELOPMENT:
            return self.development_actor()
        raise SecurityAuthenticationError("credentials_missing")

    def internal_actor(self, envelope: str) -> Actor:
        try:
            actor = self.bearer.authenticate(envelope)
        except InvalidBearerTokenError as error:
            raise SecurityAuthenticationError("invalid_internal_actor_envelope") from error
        return actor.model_copy(update={"authentication_method": AuthenticationMethod.TRUSTED_INTERNAL})

    def development_actor(self) -> Actor:
        return Actor(
            id=settings.SECURITY_LOCAL_ACTOR_ID,
            kind=ActorKind.HUMAN,
            authentication_method=AuthenticationMethod.LOCAL_DEVELOPMENT,
            permissions=("*",),
            session_id="local-development",
        )

    def bind(self, request: HttpRequest, actor: Actor, intent_json: str) -> None:
        request.META[self.ACTOR_CONTEXT_KEY] = actor.model_dump_json()
        request.META[self.INTENT_CONTEXT_KEY] = intent_json

    def bound_actor(self, request: HttpRequest) -> Actor:
        return Actor.model_validate_json(request.META[self.ACTOR_CONTEXT_KEY])
