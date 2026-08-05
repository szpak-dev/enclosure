from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, field_validator

from ...errors import ScaffoldingError


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
    StringVariable
    | IntegerVariable
    | NumberVariable
    | BooleanVariable
    | ArrayVariable
    | ObjectVariable,
    Field(discriminator="type"),
]
