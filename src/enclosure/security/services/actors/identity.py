from dataclasses import dataclass
from typing import ClassVar

from django.conf import settings
from django.core import signing
from wireup import injectable

from .contract import BearerIdentityProvider
from .errors import InvalidBearerTokenError
from .model import Actor


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
