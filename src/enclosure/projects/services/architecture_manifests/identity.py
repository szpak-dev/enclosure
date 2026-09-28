from pydantic import BaseModel, ConfigDict


class ArchitectureComparisonIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 3
    revision: str = "architecture-contract-comparator-v3"
