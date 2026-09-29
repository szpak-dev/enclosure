from pydantic import BaseModel, ConfigDict, Field

from ...architecture_manifests.identity import ArchitectureComparisonIdentity


class ArchitectureConformanceIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    producer: str = "enclosure.architecture-conformance"
    producer_revision: str = "2"
    comparison: ArchitectureComparisonIdentity = Field(default_factory=ArchitectureComparisonIdentity)
    attestation_schema_version: int = 2
