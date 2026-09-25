from django.conf import settings
from starlette.types import ASGIApp

from enclosure.security.services.actors import DjangoSignedBearerIdentityProvider

from .adapters.protocol import McpActorAuthenticator, McpProtocolServer, McpTokenVerifierAdapter


class McpApplication:
    def build(self) -> ASGIApp:
        bearer = DjangoSignedBearerIdentityProvider()
        return McpProtocolServer(
            release=settings.RELEASE_VERSION,
            actor_authenticator=McpActorAuthenticator(),
            token_verifier=McpTokenVerifierAdapter(bearer=bearer),
        ).build()
