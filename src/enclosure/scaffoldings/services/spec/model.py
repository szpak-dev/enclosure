from typing import Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from enclosure.shared.source_code.package import SourceCodePackage

from ...errors import ScaffoldingError
from .template import Template
from .variables import Variable


class ScaffoldingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    language: str = Field(description="Language identifier for the rendered source code.", min_length=1)
    variables: tuple[Variable, ...] = Field(
        default=(),
        description="Parameters accepted when rendering the scaffolding.",
    )
    templates: tuple[Template, ...] = Field(description="Source file templates rendered by the scaffolding.")

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        variable_names = tuple(variable.name for variable in self.variables)
        duplicate_variable_names = sorted(name for name in set(variable_names) if variable_names.count(name) > 1)
        if duplicate_variable_names:
            rendered_names = ", ".join(duplicate_variable_names)
            raise ScaffoldingError(f"Scaffolding variable names must be unique: {rendered_names}")

        template_paths = tuple(template.path for template in self.templates)
        duplicate_template_paths = sorted(path for path in set(template_paths) if template_paths.count(path) > 1)
        if duplicate_template_paths:
            rendered_paths = ", ".join(duplicate_template_paths)
            raise ScaffoldingError(f"Scaffolding template paths must be unique: {rendered_paths}")

        template_path_set = set(template_paths)
        topology_conflicts: list[tuple[str, str]] = []
        for path in template_paths:
            parts = path.split("/")
            for index in range(1, len(parts)):
                ancestor = "/".join(parts[:index])
                if ancestor in template_path_set:
                    topology_conflicts.append((ancestor, path))

        if topology_conflicts:
            rendered_conflicts = ", ".join(
                f"{ancestor} and {descendant}" for ancestor, descendant in sorted(topology_conflicts)
            )
            raise ScaffoldingError(
                f"Scaffolding template paths conflict as files and directories: {rendered_conflicts}"
            )
        return self


class PreparedScaffolding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spec: ScaffoldingSpec
    source: SourceCodePackage
    parameters: dict[str, JsonValue]
