from typing import Annotated

from ninja import Schema
from pydantic import Field, JsonValue

from ..services.spec.model import ScaffoldingSpec

ScaffoldingId = Annotated[str, Field(description="Scaffolding identifier.")]


class ScaffoldingInput(Schema):
    language_id: str = Field(description="Language identifier for the rendered source code.")
    name: str = Field(description="Human-readable scaffolding name.")
    description: str = Field(description="Purpose and intended use of the scaffolding.")
    spec: ScaffoldingSpec = Field(description="Templates and parameters used to render source code.")


class ScaffoldingSummary(Schema):
    id: ScaffoldingId
    language_id: str = Field(description="Language identifier for the rendered source code.")
    name: str = Field(description="Human-readable scaffolding name.")
    description: str = Field(description="Purpose and intended use of the scaffolding.")


class Scaffolding(ScaffoldingSummary):
    spec: ScaffoldingSpec = Field(description="Templates and parameters used to render source code.")


class GenerateSourceCode(Schema):
    parameters: dict[str, JsonValue] = Field(
        description="Values for variables declared by the scaffolding specification."
    )


class Rendering(Schema):
    files: dict[str, str] = Field(description="Rendered source files keyed by relative path.")
