from collections.abc import Iterable
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, ValidationError, field_validator, model_validator

from enclosure.shared.source_code.package import SourceCodePackage

from ...errors import ScaffoldingError


class WriteMode(StrEnum):
    OVERWRITE = "overwrite"
    CREATE_IF_MISSING = "create_if_missing"


class Template(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(description="Relative output path of the rendered file.")
    content: str = Field(description="Template source rendered into the output file.")
    write_mode: WriteMode = Field(
        default=WriteMode.OVERWRITE,
        description="Whether rendering may replace an existing file.",
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, path: str) -> str:
        try:
            SourceCodePackage.model_validate(
                {"language": "", "package": {"files": {path: ""}}},
            )
        except ValidationError as error:
            raise ScaffoldingError(error.errors()[0]["msg"]) from error
        return path


class VariableType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class BaseVariable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(description="Parameter name referenced by scaffolding templates.")

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        if not name.isidentifier():
            raise ScaffoldingError("Variable names must be valid Python-style identifiers.")
        return name


class StringVariable(BaseVariable):
    type: Literal[VariableType.STRING] = Field(
        default=VariableType.STRING,
        description="Value type required for the parameter.",
    )

    def validate_value(self, value: JsonValue) -> JsonValue:
        return TypeAdapter(str).validate_python(value, strict=True)


class IntegerVariable(BaseVariable):
    type: Literal[VariableType.INTEGER] = Field(
        default=VariableType.INTEGER,
        description="Value type required for the parameter.",
    )

    def validate_value(self, value: JsonValue) -> JsonValue:
        return TypeAdapter(int).validate_python(value, strict=True)


class NumberVariable(BaseVariable):
    type: Literal[VariableType.NUMBER] = Field(
        default=VariableType.NUMBER,
        description="Value type required for the parameter.",
    )

    def validate_value(self, value: JsonValue) -> JsonValue:
        return TypeAdapter(int | float).validate_python(value, strict=True)


class BooleanVariable(BaseVariable):
    type: Literal[VariableType.BOOLEAN] = Field(
        default=VariableType.BOOLEAN,
        description="Value type required for the parameter.",
    )

    def validate_value(self, value: JsonValue) -> JsonValue:
        return TypeAdapter(bool).validate_python(value, strict=True)


class ArrayVariable(BaseVariable):
    type: Literal[VariableType.ARRAY] = Field(
        default=VariableType.ARRAY,
        description="Value type required for the parameter.",
    )

    def validate_value(self, value: JsonValue) -> JsonValue:
        return TypeAdapter(list[JsonValue]).validate_python(value, strict=True)


class ObjectVariable(BaseVariable):
    type: Literal[VariableType.OBJECT] = Field(
        default=VariableType.OBJECT,
        description="Value type required for the parameter.",
    )

    def validate_value(self, value: JsonValue) -> JsonValue:
        return TypeAdapter(dict[str, JsonValue]).validate_python(value, strict=True)


Variable = Annotated[
    StringVariable | IntegerVariable | NumberVariable | BooleanVariable | ArrayVariable | ObjectVariable,
    Field(discriminator="type"),
]


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
