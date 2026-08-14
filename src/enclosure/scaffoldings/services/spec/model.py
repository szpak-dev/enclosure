from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from enclosure.shared import SourceCodePackage

from ...errors import ScaffoldingError
from .template import Template
from .variables import Variable


class ScaffoldingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    language: str = Field(description="Language identifier for the rendered source code.")
    variables: tuple[Variable, ...] = Field(
        default=(),
        description="Parameters accepted when rendering the scaffolding.",
    )
    templates: tuple[Template, ...] = Field(description="Source file templates rendered by the scaffolding.")

    @model_validator(mode="after")
    def validate_unique_members(self) -> "ScaffoldingSpec":
        self._validate_unique("variable", (variable.name for variable in self.variables))
        self._validate_unique("template", (template.path for template in self.templates))
        return self

    @staticmethod
    def _validate_unique(member: str, values: Iterable[str]) -> None:
        seen: set[str] = set()
        duplicates: set[str] = set()

        for value in values:
            if value in seen:
                duplicates.add(value)
            seen.add(value)

        if duplicates:
            rendered_duplicates = ", ".join(sorted(duplicates))
            raise ScaffoldingError(f"Scaffolding {member} names must be unique: {rendered_duplicates}")


class PreparedScaffolding(BaseModel):
    model_config = ConfigDict(frozen=True)

    spec: ScaffoldingSpec
    source: SourceCodePackage
    parameters: dict[str, JsonValue]
