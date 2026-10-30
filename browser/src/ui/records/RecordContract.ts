import {
  Action,
  EmbeddedLink,
  Field,
  type Entity,
  type SubEntity,
  type Target,
} from "@siren-js/client";

export type JsonValue =
  string | number | boolean | null | JsonValue[] | JsonObject;
export type JsonObject = { [name: string]: JsonValue };
export type Available<T> =
  { kind: "available"; value: T } | { kind: "unavailable" };
export type RecordTag = { id: string; name: string };
export type RecordCategory = { id: string; title: string; version: number };
export type RecordSummary = {
  id: string;
  title: string;
  category: RecordCategory;
  version: number;
  tags: RecordTag[];
};
export type ResourceInput = { path: string; language: string; content: string };
export type ResourceManifest = {
  path: string;
  language: string;
  mediaType: string;
  size: number;
  revision: string;
};
export type RecordDetail = RecordSummary & {
  content: JsonObject;
  contentRevision: string;
  resourcesRevision: string;
  resourceCount: number;
  resources: ResourceManifest[];
};
export type RecordDraft = {
  title: string;
  categoryId: string;
  tagIds: string[];
  content: string;
  resources: ResourceInput[];
};
export type RecordChoice = { value: string; label: string; target: Target };

export class RecordContract {
  object(value: unknown): Record<string, unknown> {
    if (typeof value !== "object" || value === null || Array.isArray(value))
      throw new Error("The server returned an incomplete Records document.");
    return Object.fromEntries(Object.entries(value));
  }

  string(value: unknown): string {
    if (typeof value !== "string")
      throw new Error("The server returned a missing or invalid text field.");
    return value;
  }

  number(value: unknown): number {
    if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0)
      throw new Error("The server returned an invalid count or version.");
    return value;
  }

  array(value: unknown): unknown[] {
    if (!Array.isArray(value))
      throw new Error("The server returned an invalid Records collection.");
    return value;
  }

  json(value: unknown): JsonValue {
    if (
      value === null ||
      typeof value === "string" ||
      typeof value === "boolean"
    )
      return value;
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (Array.isArray(value))
      return value.map((item: unknown) => this.json(item));
    return Object.fromEntries(
      Object.entries(this.object(value)).map(([name, item]) => [
        name,
        this.json(item),
      ]),
    );
  }

  jsonObject(value: unknown): JsonObject {
    return Object.fromEntries(
      Object.entries(this.object(value)).map(([name, item]) => [
        name,
        this.json(item),
      ]),
    );
  }

  parseContent(source: string): JsonObject {
    const value: unknown = JSON.parse(source);
    return this.jsonObject(value);
  }

  category(value: unknown): RecordCategory {
    const data = this.object(value);
    return {
      id: this.string(data.id),
      title: this.string(data.title),
      version: this.number(data.schema_version),
    };
  }

  tag(value: unknown): RecordTag {
    const data = this.object(value);
    return { id: this.string(data.id), name: this.string(data.name) };
  }

  summary(value: unknown): RecordSummary {
    const data = this.object(value);
    return {
      id: this.string(data.id),
      title: this.string(data.title),
      category: this.category(data.category),
      version: this.number(data.schema_version),
      tags: this.array(data.tags).map((tag) => this.tag(tag)),
    };
  }

  manifest(value: unknown): ResourceManifest {
    const data = this.object(value);
    return {
      path: this.string(data.path),
      language: this.string(data.language),
      mediaType: this.string(data.media_type),
      size: this.number(data.size_bytes),
      revision: this.string(data.revision),
    };
  }

  detail(entity: Entity): RecordDetail {
    const data = this.object(entity.properties);
    return {
      ...this.summary(data),
      content: this.jsonObject(data.content),
      contentRevision: this.string(data.content_revision),
      resourcesRevision: this.string(data.resources_revision),
      resourceCount: this.number(data.resource_count),
      resources: this.array(data.resources).map((item) => this.manifest(item)),
    };
  }

  properties(item: SubEntity): object {
    if (item instanceof EmbeddedLink)
      throw new Error(
        "Records metadata is unavailable. Open the resource to reload it.",
      );
    return item.properties;
  }

  target(entity: Entity | SubEntity): Available<Target> {
    if (entity instanceof EmbeddedLink)
      return { kind: "available", value: entity };
    for (const rel of ["item", "self"]) {
      const link = entity.links.find((candidate) =>
        candidate.rel.includes(rel),
      );
      if (link) return { kind: "available", value: link };
    }
    return { kind: "unavailable" };
  }

  action(entity: Entity | SubEntity, name: string): Available<Action> {
    if (entity instanceof EmbeddedLink) return { kind: "unavailable" };
    const action = entity.actions.find((candidate) => candidate.name === name);
    return action
      ? { kind: "available", value: action }
      : { kind: "unavailable" };
  }

  collection(
    root: Entity,
    name: "records" | "categories" | "tags" | "languages",
  ): Available<Target> {
    const suffix =
      name === "records" || name === "languages"
        ? `/${name}`
        : `/records/${name}`;
    const link = root.links.find(
      (candidate) =>
        candidate.rel.includes("collection") &&
        new URL(candidate.href.toString(), window.location.origin).pathname
          .replace(/\/$/, "")
          .endsWith(suffix),
    );
    return link ? { kind: "available", value: link } : { kind: "unavailable" };
  }

  required<T>(value: Available<T>, message: string): T {
    if (value.kind === "unavailable") throw new Error(message);
    return value.value;
  }

  href(target: Target): string {
    return (typeof target === "string" ? target : target.href).toString();
  }

  query(target: Target, values: Record<string, string | number>): string {
    const url = new URL(this.href(target), window.location.origin);
    for (const [name, value] of Object.entries(values))
      url.searchParams.set(name, String(value));
    return url.toString();
  }

  next(entity: Entity): Available<Target> {
    const next = entity.links.find((link) => link.rel.includes("next"));
    return next ? { kind: "available", value: next } : { kind: "unavailable" };
  }

  writeAction(action: Action, values: Record<string, unknown>): Action {
    return Object.assign(new Action(), action, {
      fields: Object.entries(values).map(([name, value]) =>
        Object.assign(new Field(), {
          name,
          value,
          type: typeof value === "object" ? "hidden" : "text",
        }),
      ),
    });
  }

  message(reason: unknown): string {
    return reason instanceof Error
      ? reason.message
      : "The request could not be completed. Try again.";
  }
}

export const recordContract = new RecordContract();
