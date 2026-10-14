from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, ValidationError, model_validator

from enclosure.shared.source_code.errors import SourceCodeError
from enclosure.shared.source_code.package import CodePackage, SourceCodePackage

from ...errors import ScaffoldingError


class WriteMode(StrEnum):
    OVERWRITE = "overwrite"
    CREATE_IF_MISSING = "create_if_missing"


class VariableType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class Variable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(description="Parameter name referenced by scaffolding templates.")
    type: VariableType = Field(description="Value type required for the parameter.")

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if not self.name.isidentifier():
            raise ScaffoldingError(f"Scaffolding variable name must be a valid identifier: {self.name!r}")
        return self

    def validate_value(self, value: JsonValue) -> JsonValue:
        try:
            if self.type == VariableType.STRING:
                return TypeAdapter(str).validate_python(value, strict=True)
            if self.type == VariableType.INTEGER:
                return TypeAdapter(int).validate_python(value, strict=True)
            if self.type == VariableType.NUMBER:
                return TypeAdapter(int | float).validate_python(value, strict=True)
            if self.type == VariableType.BOOLEAN:
                return TypeAdapter(bool).validate_python(value, strict=True)
            if self.type == VariableType.ARRAY:
                return TypeAdapter(list[JsonValue]).validate_python(value, strict=True)
            return TypeAdapter(dict[str, JsonValue]).validate_python(value, strict=True)
        except ValidationError as error:
            raise ScaffoldingError(f"Rendering parameter {self.name!r} must have type {self.type.value!r}.") from error


class Template(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(description="Relative output path of the rendered file.")
    content: str = Field(description="Template source rendered into the output file.")
    write_mode: WriteMode = Field(
        default=WriteMode.OVERWRITE,
        description="Whether rendering may replace an existing file.",
    )

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        try:
            CodePackage(files={self.path: self.content})
        except SourceCodeError as error:
            raise ScaffoldingError(f"Invalid scaffolding template path {self.path!r}: {error}") from error
        if not self.path.endswith(".jinja") and any(token in self.content for token in ("{{", "{%", "{#")):
            raise ScaffoldingError("Template content uses Jinja syntax; its path must end with '.jinja'.")
        return self


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
