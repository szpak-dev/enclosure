from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ActorKind(StrEnum):
    HUMAN = "human"
    SERVICE = "service"


class AuthenticationMethod(StrEnum):
    SESSION = "session"
    BEARER = "bearer"
    TRUSTED_INTERNAL = "trusted_internal"
    LOCAL_DEVELOPMENT = "local_development"


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    kind: ActorKind
    authentication_method: AuthenticationMethod
    permissions: tuple[str, ...]
    session_id: str
