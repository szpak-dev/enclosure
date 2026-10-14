from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, ValidationError, model_validator

from ...errors import ScaffoldingError


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
            raise ScaffoldingError(
                f"Rendering parameter {self.name!r} must have type {self.type.value!r}."
            ) from error
