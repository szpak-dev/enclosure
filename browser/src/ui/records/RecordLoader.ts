import type { Entity, Target } from "@siren-js/client";
import Ajv2020 from "ajv/dist/2020";
import type { RJSFSchema } from "@rjsf/utils";
import {
  recordContract as contract,
  type Available,
  type RecordChoice,
  type RecordDetail,
  type RecordDraft,
  type ResourceInput,
} from "./RecordContract";

export type ContentSchema =
  | { kind: "available"; schema: RJSFSchema; version: number }
  | { kind: "historical"; version: number };
export type PreparedRecord = {
  draft: RecordDraft;
  categories: RecordChoice[];
  tags: RecordChoice[];
  languages: RecordChoice[];
  original: Available<RecordDetail>;
};

export class RecordLoader {
  private readonly validator = new Ajv2020({ strict: false });
  constructor(private readonly load: (target: Target) => Promise<Entity>) {}

  async choices(
    root: Entity,
    kind: "categories" | "tags" | "languages",
  ): Promise<RecordChoice[]> {
    let target = contract.required(
      contract.collection(root, kind),
      `${kind} navigation is unavailable.`,
    );
    const choices: RecordChoice[] = [];
    const seen = new Set<string>();
    while (true) {
      this.visit(seen, target);
      const page = await this.load(target);
      for (const item of page.entities) {
        const data = contract.object(contract.properties(item));
        choices.push({
          value: contract.string(data.id),
          label: contract.string(
            kind === "categories" ? data.title : data.name,
          ),
          target: contract.required(
            contract.target(item),
            `A ${kind} item cannot be opened.`,
          ),
        });
      }
      const next = contract.next(page);
      if (next.kind === "unavailable") return choices;
      target = next.value;
    }
  }

  async prepare(
    root: Entity,
    source: Available<Target>,
  ): Promise<PreparedRecord> {
    const [categories, tags, languages] = await Promise.all([
      this.choices(root, "categories"),
      this.choices(root, "tags"),
      this.choices(root, "languages"),
    ]);
    if (source.kind === "unavailable")
      return {
        categories,
        tags,
        languages,
        original: { kind: "unavailable" },
        draft: {
          title: "",
          categoryId: "",
          tagIds: [],
          content: "{}",
          resources: [],
        },
      };
    const entity = await this.load(source.value);
    const detail = contract.detail(entity);
    const resources = await this.resources(entity, detail);
    return {
      categories,
      tags,
      languages,
      original: { kind: "available", value: detail },
      draft: {
        title: detail.title,
        categoryId: detail.category.id,
        tagIds: detail.tags.map((tag) => tag.id),
        content: JSON.stringify(detail.content, null, 2),
        resources,
      },
    };
  }

  async schema(
    choice: RecordChoice,
    original: Available<RecordDetail>,
  ): Promise<ContentSchema> {
    const entity = await this.load(choice.target);
    const data = contract.object(entity.properties);
    const version = contract.number(data.schema_version);
    if (
      original.kind === "available" &&
      original.value.category.id === choice.value &&
      original.value.version !== version
    )
      return { kind: "historical", version: original.value.version };
    const revision = contract.string(data.content_schema_revision);
    const action = contract.required(
      contract.action(entity, "read_record_category_content_schema"),
      "Schema inspection is unavailable.",
    );
    const target = contract.query(action, {
      expected_revision: revision,
      schema_version: version,
      offset: 0,
      limit: 10000,
    });
    const source = await this.text(target, revision, {
      category_id: choice.value,
      schema_version: version,
    });
    const value: unknown = JSON.parse(source);
    if (!this.isSchema(value))
      throw new Error("The category returned an invalid JSON Schema.");
    return { kind: "available", schema: value, version };
  }

  private isSchema(value: unknown): value is RJSFSchema {
    return (
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value) &&
      this.validator.validateSchema(value) === true
    );
  }

  async resources(
    entity: Entity,
    detail: RecordDetail,
  ): Promise<ResourceInput[]> {
    const link = entity.links.find(
      (candidate) =>
        candidate.rel.includes("collection") &&
        new URL(
          candidate.href.toString(),
          window.location.origin,
        ).pathname.endsWith("/resource-manifests"),
    );
    if (!link)
      throw new Error("The record does not advertise its resource manifests.");
    let target: Target = contract.query(link, {
      expected_revision: detail.resourcesRevision,
      offset: 0,
      limit: 50,
    });
    const resources: ResourceInput[] = [];
    const seen = new Set<string>();
    while (true) {
      this.visit(seen, target);
      const page = await this.load(target);
      const data = contract.object(page.properties);
      if (
        contract.string(data.revision) !== detail.resourcesRevision ||
        contract.string(data.record_id) !== detail.id
      )
        throw new Error("Resources changed. Reload the record before editing.");
      for (const item of page.entities) {
        const manifest = contract.manifest(contract.properties(item));
        const sourceTarget = contract.required(
          contract.target(item),
          "A resource does not advertise its content.",
        );
        const content = await this.text(
          contract.query(sourceTarget, {
            expected_revision: manifest.revision,
            path: manifest.path,
            offset: 0,
            limit: 10000,
          }),
          manifest.revision,
          {
            record_id: detail.id,
            path: manifest.path,
            language: manifest.language,
          },
        );
        resources.push({
          path: manifest.path,
          language: manifest.language,
          content,
        });
      }
      const next = contract.next(page);
      if (next.kind === "unavailable") break;
      target = next.value;
    }
    if (
      resources.length !== detail.resourceCount ||
      new Set(resources.map((item) => item.path)).size !== resources.length
    )
      throw new Error(
        "The complete attachment set could not be loaded. Reload the record.",
      );
    return resources;
  }

  async text(
    target: Target,
    revision: string,
    identity: Record<string, string | number>,
  ): Promise<string> {
    const seen = new Set<string>();
    let content = "";
    while (true) {
      this.visit(seen, target);
      const page = await this.load(target);
      const data = contract.object(page.properties);
      if (
        contract.string(data.revision) !== revision ||
        Object.entries(identity).some(
          ([name, value]) => data[name] !== value,
        ) ||
        contract.number(data.offset) !== Array.from(content).length
      )
        throw new Error(
          "This document changed or returned an incomplete page. Reload before continuing.",
        );
      const chunk = contract.string(data.content);
      content += chunk;
      const total = contract.number(data.total_characters);
      const next = contract.next(page);
      if (next.kind === "unavailable") {
        if (data.has_more !== false || Array.from(content).length !== total)
          throw new Error("The complete source document could not be loaded.");
        return content;
      }
      if (
        !chunk.length ||
        data.has_more !== true ||
        contract.number(data.next_offset) !== Array.from(content).length
      )
        throw new Error(
          "The source document returned an invalid continuation.",
        );
      target = next.value;
    }
  }

  private visit(seen: Set<string>, target: Target): void {
    const href = contract.href(target);
    if (seen.has(href))
      throw new Error(
        "The server returned a repeated continuation. Reload and try again.",
      );
    seen.add(href);
  }
}
