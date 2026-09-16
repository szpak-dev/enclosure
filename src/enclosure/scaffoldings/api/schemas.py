from typing import Annotated, Literal

from ninja import Schema
from pydantic import Field, JsonValue

ScaffoldingId = Annotated[str, Field(description="Scaffolding identifier.")]


class ScaffoldingVariableInput(Schema):
    name: str = Field(description="Parameter name referenced by scaffolding templates.")
    type: Literal["string", "integer", "number", "boolean", "array", "object"] = Field(
        default="string", description="Value type required for the parameter."
    )


class ScaffoldingTemplateInput(Schema):
    path: str = Field(description="Relative output path of the rendered file.")
    content: str = Field(description="Template source rendered into the output file.")
    write_mode: Literal["overwrite", "create_if_missing"] = Field(
        default="overwrite",
        description="Whether rendering may replace an existing file.",
    )


class ScaffoldingSpecInput(Schema):
    language: str = Field(description="Language identifier for the rendered source code.")
    variables: list[ScaffoldingVariableInput] = Field(
        default_factory=list,
        description="Parameters accepted when rendering the scaffolding.",
    )
    templates: list[ScaffoldingTemplateInput] = Field(description="Source file templates rendered by the scaffolding.")


class ScaffoldingInput(Schema):
    language_id: str = Field(description="Language identifier for the rendered source code.")
    name: str = Field(description="Human-readable scaffolding name.")
    description: str = Field(description="Purpose and intended use of the scaffolding.")
    spec: ScaffoldingSpecInput = Field(description="Templates and parameters used to render source code.")


class ScaffoldingSummary(Schema):
    id: ScaffoldingId
    language_id: str = Field(description="Language identifier for the rendered source code.")
    name: str = Field(description="Human-readable scaffolding name.")
    description: str = Field(description="Purpose and intended use of the scaffolding.")


class TemplateManifest(Schema):
    path: str = Field(description="Exact relative template path.")
    write_mode: Literal["overwrite", "create_if_missing"] = Field(
        description="Write policy applied to the rendered file."
    )
    size_bytes: int = Field(description="Complete template size in bytes.", ge=0)
    revision: str = Field(description="SHA-256 revision of the complete template content.")


class ScaffoldingSpecManifest(Schema):
    language: str = Field(description="Language identifier declared by the scaffolding specification.")
    variables: list[dict[str, JsonValue]] = Field(description="Rendering variable declarations.")
    templates: list[TemplateManifest] = Field(description="Template manifests without complete bodies.")


class Scaffolding(ScaffoldingSummary):
    spec: ScaffoldingSpecManifest = Field(description="Variables and bounded template manifests.")


class FindPage(Schema):
    offset: int = Field(default=0, description="Item offset at which the page starts.", ge=0)
    limit: int = Field(default=50, description="Maximum items returned by the page.", ge=1, le=100)


class ScaffoldingPage(Schema):
    items: list[ScaffoldingSummary] = Field(description="Compact scaffolding references in this bounded page.")
    has_more: bool = Field(description="Whether another scaffolding page remains.")
    next_offset: int = Field(description="Item offset for the next page.", ge=0)
    limit: int = Field(description="Maximum items requested for this page.", ge=1, le=100)


class SearchScaffoldings(Schema):
    name: str = Field(description="Scaffolding name or fragment to match.", min_length=1, pattern=r"\S")
    language_id: str = Field(default="", description="Optional exact language identifier.")
    limit: int = Field(default=10, description="Maximum references returned.", ge=1, le=100)


class ReadScaffoldingTemplate(Schema):
    path: str = Field(description="Exact template path from the manifest.", min_length=1)
    expected_revision: str = Field(
        description="SHA-256 template revision on which the read is based.", pattern=r"^[0-9a-f]{64}$"
    )
    offset: int = Field(default=0, description="Character offset at which the read starts.", ge=0)
    limit: int = Field(default=512, description="Maximum characters returned.", ge=1, le=512)


class ScaffoldingTemplateContent(Schema):
    scaffolding_id: ScaffoldingId
    path: str = Field(description="Exact relative template path.")
    write_mode: Literal["overwrite", "create_if_missing"] = Field(
        description="Write policy applied to the rendered file."
    )
    revision: str = Field(description="SHA-256 revision of the complete template content.")
    offset: int = Field(description="Character offset at which this page starts.", ge=0)
    limit: int = Field(description="Maximum characters requested for this page.", ge=1, le=512)
    total_characters: int = Field(description="Total characters in the template body.", ge=0)
    content: str = Field(description="Bounded template content.")
    has_more: bool = Field(description="Whether another bounded page remains.")
    next_offset: int = Field(description="Character offset for the next read.", ge=0)


class RenderScaffolding(Schema):
    parameters: dict[str, JsonValue] = Field(description="Values for declared scaffolding variables.")
    offset: int = Field(default=0, description="Rendered-file offset at which the page starts.", ge=0)
    limit: int = Field(default=10, description="Maximum rendered-file manifests returned.", ge=1, le=50)


class RenderedFileManifest(Schema):
    path: str = Field(description="Exact rendered output path.")
    overwrite: bool = Field(description="Whether generation may replace an existing file.")
    size_bytes: int = Field(description="Complete rendered file size in bytes.", ge=0)
    revision: str = Field(description="SHA-256 revision of the complete rendered content.")
    preview: str = Field(description="At most 256 characters of rendered content.")


class RenderingPage(Schema):
    scaffolding_id: ScaffoldingId
    items: list[RenderedFileManifest] = Field(description="Rendered-file manifests in this bounded page.")
    has_more: bool = Field(description="Whether another rendered-file page remains.")
    next_offset: int = Field(description="Rendered-file offset for the next page.", ge=0)
    limit: int = Field(description="Maximum manifests requested for this page.", ge=1, le=50)


class ReadScaffoldingRenderedFile(Schema):
    parameters: dict[str, JsonValue] = Field(description="The parameters used to produce the file manifest.")
    path: str = Field(description="Exact path from the rendered-file manifest.", min_length=1)
    expected_revision: str = Field(
        description="SHA-256 rendered-file revision on which the read is based.", pattern=r"^[0-9a-f]{64}$"
    )
    offset: int = Field(default=0, description="Character offset at which the read starts.", ge=0)
    limit: int = Field(default=512, description="Maximum characters returned.", ge=1, le=512)


class RenderedFileContent(Schema):
    scaffolding_id: ScaffoldingId
    path: str = Field(description="Exact rendered output path.")
    overwrite: bool = Field(description="Whether generation may replace an existing file.")
    revision: str = Field(description="SHA-256 revision of the complete rendered content.")
    offset: int = Field(description="Character offset at which this page starts.", ge=0)
    limit: int = Field(description="Maximum characters requested for this page.", ge=1, le=512)
    total_characters: int = Field(description="Total characters in the rendered file.", ge=0)
    content: str = Field(description="Bounded rendered-file content.")
    has_more: bool = Field(description="Whether another bounded page remains.")
    next_offset: int = Field(description="Character offset for the next read.", ge=0)
