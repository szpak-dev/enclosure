from pydantic import BaseModel, ConfigDict


class ArchitectureComparisonIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 4
    revision: str = "language-neutral-architecture-comparator-v4"
