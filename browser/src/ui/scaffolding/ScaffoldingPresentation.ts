import {
  Action,
  EmbeddedLink,
  type Entity,
  type Link,
  type SubEntity,
  type Target,
} from "@siren-js/client";
import {
  OBJECT_CONTROL,
  STRUCTURED_FORM_EXTENSION,
} from "../siren/SirenActionForm";

export type PresentedTarget =
  { kind: "present"; target: Target } | { kind: "absent" };

export type ScaffoldingVariableType =
  "string" | "integer" | "number" | "boolean" | "array" | "object";

export type ScaffoldingVariable = {
  name: string;
  type: ScaffoldingVariableType;
};

export type TemplateManifest = {
  path: string;
  revision: string;
  sizeBytes: number;
  writeMode: string;
};

export type ScaffoldingSpec = {
  language: string;
  templates: readonly TemplateManifest[];
  variables: readonly ScaffoldingVariable[];
};

export type ScaffoldingSpecState =
  { kind: "available"; spec: ScaffoldingSpec } | { kind: "unavailable" };

export type RenderedFileManifest = {
  overwrite: boolean;
  path: string;
  preview: string;
  revision: string;
  sizeBytes: number;
};

export class ScaffoldingPresentation {
  value(properties: object, name: string): unknown {
    return Object.entries(properties).find(([key]) => key === name)?.[1];
  }

  text(properties: object, name: string): string {
    const value = this.value(properties, name);
    if (typeof value === "string") return value.trim() ? value : "Not reported";
    if (typeof value === "number") return String(value);
    if (typeof value === "boolean") return value ? "Yes" : "No";
    return "Not reported";
  }

  string(properties: object, name: string): string | undefined {
    const value = this.value(properties, name);
    return typeof value === "string" ? value : undefined;
  }

  integer(properties: object, name: string): number | undefined {
    const value = this.value(properties, name);
    return typeof value === "number" && Number.isInteger(value)
      ? value
      : undefined;
  }

  boolean(properties: object, name: string): boolean | undefined {
    const value = this.value(properties, name);
    return typeof value === "boolean" ? value : undefined;
  }

  itemProperties(item: SubEntity): object {
    return item instanceof EmbeddedLink ? {} : item.properties;
  }

  itemTarget(item: SubEntity): PresentedTarget {
    if (item instanceof EmbeddedLink) return { kind: "present", target: item };
    const itemLink = item.links.find((link) => link.rel.includes("item"));
    return itemLink
      ? { kind: "present", target: itemLink }
      : { kind: "absent" };
  }

  label(value: string): string {
    const labels: Record<string, string> = {
      expected_revision: "Expected revision",
      has_more: "More available",
      language_id: "Language",
      next_offset: "Next offset",
      overwrite: "May overwrite",
      scaffolding_id: "Scaffolding ID",
      size_bytes: "Size",
      template_count: "Templates",
      templates_revision: "Template-set revision",
      total_characters: "Total characters",
      write_mode: "Write mode",
    };
    const known = labels[value];
    if (known) return known;
    return value
      .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
      .replace(/_/g, " ")
      .replace(/^./, (character) => character.toUpperCase());
  }

  linkLabel(link: Link): string {
    return link.title ? this.label(link.title) : "Related resource";
  }

  spec(properties: object): ScaffoldingSpecState {
    const rawSpec = this.record(this.value(properties, "spec"));
    if (!rawSpec) return { kind: "unavailable" };
    const language = this.value(rawSpec, "language");
    const rawVariables = this.value(rawSpec, "variables");
    const rawTemplates = this.value(rawSpec, "templates");
    if (
      typeof language !== "string" ||
      !Array.isArray(rawVariables) ||
      !Array.isArray(rawTemplates)
    )
      return { kind: "unavailable" };
    const variables = rawVariables.map((value) => this.variable(value));
    const templates = rawTemplates.map((value) => this.template(value));
    if (
      variables.some((value) => value === undefined) ||
      templates.some((value) => value === undefined)
    )
      return { kind: "unavailable" };
    return {
      kind: "available",
      spec: {
        language,
        templates: templates.filter(
          (value): value is TemplateManifest => value !== undefined,
        ),
        variables: variables.filter(
          (value): value is ScaffoldingVariable => value !== undefined,
        ),
      },
    };
  }

  manifestTarget(entity: Entity): PresentedTarget {
    const link = entity.links.find(
      (candidate) =>
        candidate.rel.includes("collection") &&
        candidate.href.toString().includes("/template-manifests"),
    );
    const revision = this.value(entity.properties, "templates_revision");
    if (!link || typeof revision !== "string") return { kind: "absent" };
    const target = new URL(link.href.toString(), window.location.origin);
    target.searchParams.set("expected_revision", revision);
    target.searchParams.set("offset", "0");
    target.searchParams.set("limit", "50");
    return { kind: "present", target: target.toString() };
  }

  typedRenderingAction(
    action: Action,
    variables: readonly ScaffoldingVariable[],
  ): Action {
    const parameterProperties = Object.fromEntries(
      variables.map((variable) => [
        variable.name,
        this.parameterSchema(variable),
      ]),
    );
    return Object.assign(new Action(), action, {
      [STRUCTURED_FORM_EXTENSION]: {
        controls: [
          {
            control: OBJECT_CONTROL,
            location: "body",
            mediaType: "application/json",
            name: "parameters",
            required: true,
            schema: {
              additionalProperties: false,
              properties: parameterProperties,
              required: variables.map((variable) => variable.name),
              title: "Rendering parameters",
              type: "object",
            },
          },
        ],
        version: "1",
      },
    });
  }

  renderedFiles(properties: object): readonly RenderedFileManifest[] {
    const items = this.value(properties, "items");
    if (!Array.isArray(items)) return [];
    return items
      .map((value) => this.renderedFile(value))
      .filter((value): value is RenderedFileManifest => value !== undefined);
  }

  private record(value: unknown): Record<string, unknown> | undefined {
    return typeof value === "object" && value !== null && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : undefined;
  }

  private variable(value: unknown): ScaffoldingVariable | undefined {
    const record = this.record(value);
    if (!record) return undefined;
    const name = this.value(record, "name");
    const type = this.value(record, "type");
    if (
      typeof name !== "string" ||
      typeof type !== "string" ||
      !["string", "integer", "number", "boolean", "array", "object"].includes(
        type,
      )
    )
      return undefined;
    return { name, type: type as ScaffoldingVariableType };
  }

  private template(value: unknown): TemplateManifest | undefined {
    const record = this.record(value);
    if (!record) return undefined;
    const path = this.value(record, "path");
    const revision = this.value(record, "revision");
    const sizeBytes = this.value(record, "size_bytes");
    const writeMode = this.value(record, "write_mode");
    if (
      typeof path !== "string" ||
      typeof revision !== "string" ||
      typeof sizeBytes !== "number" ||
      typeof writeMode !== "string"
    )
      return undefined;
    return { path, revision, sizeBytes, writeMode };
  }

  private parameterSchema(variable: ScaffoldingVariable): object {
    const common = { title: this.label(variable.name), type: variable.type };
    if (variable.type === "array") return { ...common, items: {} };
    if (variable.type === "object")
      return { ...common, additionalProperties: {} };
    return common;
  }

  private renderedFile(value: unknown): RenderedFileManifest | undefined {
    const record = this.record(value);
    if (!record) return undefined;
    const overwrite = this.value(record, "overwrite");
    const path = this.value(record, "path");
    const preview = this.value(record, "preview");
    const revision = this.value(record, "revision");
    const sizeBytes = this.value(record, "size_bytes");
    if (
      typeof overwrite !== "boolean" ||
      typeof path !== "string" ||
      typeof preview !== "string" ||
      typeof revision !== "string" ||
      typeof sizeBytes !== "number"
    )
      return undefined;
    return { overwrite, path, preview, revision, sizeBytes };
  }
}

export const scaffoldingPresentation = new ScaffoldingPresentation();
