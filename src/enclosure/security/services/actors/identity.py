from abc import ABC, abstractmethod
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import ClassVar

from django.conf import settings
from django.core import signing
from wireup import injectable

from .model import Actor


class InvalidBearerTokenError(Exception):
    """A bearer assertion is invalid or expired."""


class BearerIdentityProvider(ABC):
    @abstractmethod
    def authenticate(self, token: str) -> Actor:
        raise NotImplementedError

    @abstractmethod
    def issue(self, actor: Actor) -> str:
        raise NotImplementedError


@injectable(as_type=BearerIdentityProvider)
@dataclass(frozen=True)
class DjangoSignedBearerIdentityProvider(BearerIdentityProvider):
    salt: ClassVar[str] = "enclosure.security.actor"

    def authenticate(self, token: str) -> Actor:
        signer = signing.TimestampSigner(salt=self.salt)
        try:
            actor_json = signer.unsign(token, max_age=settings.SECURITY_BEARER_MAX_AGE_SECONDS)
        except signing.BadSignature as error:
            raise InvalidBearerTokenError("Bearer credentials are invalid or expired.") from error
        return Actor.model_validate_json(actor_json)

    def issue(self, actor: Actor) -> str:
        return signing.TimestampSigner(salt=self.salt).sign(actor.model_dump_json())


@injectable
@dataclass(frozen=True)
class ActorExecutionContext:
    actors: ContextVar[Actor] = field(default_factory=lambda: ContextVar("enclosure_actor"), init=False)

    def bind(self, actor: Actor) -> Token[Actor]:
        return self.actors.set(actor)

    def current(self) -> Actor:
        return self.actors.get()

    def reset(self, token: Token[Actor]) -> None:
        self.actors.reset(token)
