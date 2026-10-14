from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..errors import ScaffoldingError
from .spec.model import ScaffoldingSpec


class ScaffoldingCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    language_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str
    spec: ScaffoldingSpec

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if self.language_id != self.spec.language:
            raise ScaffoldingError("Scaffolding language must match its specification language.")
        return self


class ScaffoldingValue(ScaffoldingCandidate):
    id: str
