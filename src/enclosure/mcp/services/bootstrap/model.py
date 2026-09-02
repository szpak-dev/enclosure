from pydantic import BaseModel, ConfigDict


class AgentBootstrap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    uri: str
    release: str
    revision: str
    markdown: str
