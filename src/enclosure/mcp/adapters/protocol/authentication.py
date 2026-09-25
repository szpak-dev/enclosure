from dataclasses import dataclass
from hashlib import sha256

from django.conf import settings
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from enclosure.security.errors import SecurityAuthenticationError
from enclosure.security.services.actors import Actor, ActorKind, AuthenticationMethod, BearerIdentityProvider
from enclosure.security.services.actors.identity import InvalidBearerTokenError


@dataclass(frozen=True)
class McpTokenVerifierAdapter:
    bearer: BearerIdentityProvider

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            actor = self.bearer.authenticate(token)
        except InvalidBearerTokenError:
            return None
        return AccessToken(
            token=token,
            client_id=actor.kind.value,
            scopes=list(actor.permissions),
            subject=actor.id,
        )


@dataclass(frozen=True)
class McpActorAuthenticator:
    def authenticate(self) -> Actor:
        if not settings.SECURITY_MCP_AUTH_REQUIRED:
            return Actor(
                id=settings.SECURITY_LOCAL_ACTOR_ID,
                kind=ActorKind.HUMAN,
                authentication_method=AuthenticationMethod.LOCAL_DEVELOPMENT,
                permissions=("*",),
                session_id="local-development",
            )
        access_token = get_access_token()
        if access_token is None or access_token.subject is None:
            raise SecurityAuthenticationError("mcp_bearer_token_missing")
        return Actor(
            id=access_token.subject,
            kind=ActorKind(access_token.client_id),
            authentication_method=AuthenticationMethod.BEARER,
            permissions=tuple(access_token.scopes),
            session_id=sha256(access_token.token.encode()).hexdigest(),
        )

    def settings(self) -> AuthSettings:
        return AuthSettings(
            issuer_url=AnyHttpUrl(settings.SECURITY_MCP_ISSUER_URL),
            resource_server_url=AnyHttpUrl(settings.SECURITY_MCP_RESOURCE_URL),
            required_scopes=[],
        )
