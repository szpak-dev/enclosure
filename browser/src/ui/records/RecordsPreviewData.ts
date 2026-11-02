import type { Entity } from "@siren-js/client";
import { type HttpHandler } from "msw";
import { fn } from "storybook/test";
import { sirenFixtures as fixtures } from "../../stories/SirenFixtures";
import { type Available, type JsonObject } from "./RecordContract";

import { RecordsPreviewHandlers } from "./RecordsPreviewHandlers";
import type { PreviewProps, PreviewState } from "./RecordsPreviewTypes";

export class RecordsPreviewData {
  readonly revision = "a".repeat(64);
  readonly resourceRevision = "b".repeat(64);
  readonly resourceSetRevision = "c".repeat(64);
  readonly schemaRevision = "d".repeat(64);
  readonly source =
    "# Example notes\n\nKeep decisions and their supporting sources together.\n";
  readonly schema: JsonObject = {
    type: "object",
    properties: {
      summary: { type: "string", title: "Summary", minLength: 1 },
      decisions: {
        type: "array",
        title: "Decisions",
        items: { type: "string" },
      },
    },
    required: ["summary"],
    additionalProperties: false,
  };
  readonly content: JsonObject = {
    summary: "A shared place for project decisions and supporting material.",
    decisions: [
      "Keep content with its sources",
      "Review category schemas before publishing changes",
    ],
  };
  readonly base = "/siren/records";
  readonly create = fixtures.action(
    "create_record",
    "Create a record",
    this.base,
    "POST",
    [],
  );
  readonly update = fixtures.action(
    "update_record",
    "Update a record",
    `${this.base}/example`,
    "PUT",
    [],
  );
  readonly search = fixtures.action(
    "search_records",
    "Search records",
    `${this.base}/search-results`,
    "POST",
    [
      fixtures.field("query", "Query", "text"),
      fixtures.field("limit", "Limit", "number"),
    ],
  );
  saved: Available<Entity> = { kind: "unavailable" };
  readonly writes = fn<(body: object) => void>();
  failurePending = true;
  deleted = false;
  recovered = false;

  recover(): void {
    this.recovered = true;
  }

  reset(): void {
    this.saved = { kind: "unavailable" };
    this.failurePending = true;
    this.deleted = false;
    this.recovered = false;
    this.writes.mockClear();
  }
  readonly categoryCreate = fixtures.action(
    "create_record_category",
    "Create a record category",
    `${this.base}/categories`,
    "POST",
    [fixtures.field("title", "Title", "text")],
  );
  readonly tagCreate = fixtures.action(
    "create_record_tag",
    "Create a record tag",
    `${this.base}/tags`,
    "POST",
    [fixtures.field("name", "Name", "text")],
  );

  constructor(readonly scenario: PreviewState) {
    this.categoryCreate["https://modwire.dev/siren/structured-form/v1"] = {
      version: "1",
      controls: [
        {
          name: "content_schema",
          location: "body",
          required: true,
          control: "https://modwire.dev/siren/controls/json/v1",
          mediaType: "application/json",
          schema: { type: "object", additionalProperties: {} },
        },
      ],
    };
  }

  root(): Entity {
    return fixtures.entity(
      ["api", "entry-point"],
      "Enclosure API",
      { title: "Enclosure API" },
      [
        fixtures.link(this.base, ["collection"], "Record"),
        fixtures.link(`${this.base}/categories`, ["collection"], "Category"),
        fixtures.link(`${this.base}/tags`, ["collection"], "Tag"),
        fixtures.link("/siren/languages", ["collection"], "Language"),
      ],
      [],
      [this.create, this.search],
    );
  }

  summary(): JsonObject {
    return {
      id: "example",
      title: "Example decisions",
      category: {
        id: "example-notes",
        title: "Example notes",
        schema_version: 2,
      },
      schema_version: this.scenario === "historical" ? 1 : 2,
      tags: [
        { id: "example-reference", name: "example-reference" },
        { id: "example-reviewed", name: "example-reviewed" },
      ],
    };
  }

  record(): Entity {
    if (this.saved.kind === "available") return this.saved.value;
    return fixtures.entity(
      ["record"],
      "Example decisions",
      {
        ...this.summary(),
        content: this.content,
        content_revision: this.revision,
        content_total_characters: JSON.stringify(this.content).length,
        resources: [this.manifest()],
        resources_revision: this.resourceSetRevision,
        resource_count: 1,
      },
      [
        fixtures.link(`${this.base}/example`, ["self"], "Record"),
        fixtures.link(
          `${this.base}/example/resource-manifests`,
          ["collection"],
          "ResourceManifest",
        ),
      ],
      [],
      [
        this.update,
        fixtures.action(
          "delete_record",
          "Delete record",
          `${this.base}/example`,
          "DELETE",
          [],
        ),
        fixtures.action(
          "read_record_content",
          "Read content",
          `${this.base}/example/content`,
          "GET",
          [],
        ),
        fixtures.action(
          "read_record_resource",
          "Read resource",
          `${this.base}/example/resources/content`,
          "GET",
          [],
        ),
      ],
    );
  }

  collection(search: boolean): Entity {
    const item = fixtures.embeddedEntity(
      search ? ["search-result"] : ["record"],
      ["item"],
      "Example decisions",
      this.summary(),
      [fixtures.link(`${this.base}/example`, ["item"], "Record")],
    );
    if (!search) item.actions = [this.update];
    return fixtures.entity(
      ["collection", search ? "search-result" : "record"],
      search ? "RecordSummary" : "Records",
      { has_more: false, next_offset: 1, limit: 50 },
      [fixtures.link(this.base, ["self"], "Records")],
      this.scenario === "empty" ||
        this.deleted ||
        (search && this.scenario === "search-empty")
        ? []
        : [item],
      search ? [] : [this.create],
    );
  }

  category(): Entity {
    const updateSchema = fixtures.action(
      "update_record_category_content_schema",
      "Edit schema",
      `${this.base}/categories/example-notes/content-schema`,
      "PUT",
      [],
    );
    updateSchema["https://modwire.dev/siren/structured-form/v1"] =
      this.categoryCreate["https://modwire.dev/siren/structured-form/v1"];
    return fixtures.entity(
      ["category"],
      "Example notes",
      {
        id: "example-notes",
        title: "Example notes",
        schema_version: 2,
        content_schema_revision: this.schemaRevision,
        content_schema_size_bytes: JSON.stringify(this.schema).length,
      },
      [
        fixtures.link(
          `${this.base}/categories/example-notes`,
          ["self"],
          "Category",
        ),
      ],
      [],
      [
        fixtures.action(
          "update_record_category",
          "Rename category",
          `${this.base}/categories/example-notes`,
          "PUT",
          [fixtures.field("title", "Title", "text")],
        ),
        updateSchema,
        fixtures.action(
          "read_record_category_content_schema",
          "Read schema",
          `${this.base}/categories/example-notes/content-schema`,
          "GET",
          [],
        ),
        fixtures.action(
          "delete_record_category",
          "Delete category",
          `${this.base}/categories/example-notes`,
          "DELETE",
          [],
        ),
      ],
    );
  }

  tag(): Entity {
    return fixtures.entity(
      ["tag"],
      "example-reference",
      { id: "example-reference", name: "example-reference" },
      [fixtures.link(`${this.base}/tags/example-reference`, ["self"], "Tag")],
      [],
      [
        fixtures.action(
          "update_record_tag",
          "Rename tag",
          `${this.base}/tags/example-reference`,
          "PUT",
          [fixtures.field("name", "Name", "text")],
        ),
        fixtures.action(
          "delete_record_tag",
          "Delete tag",
          `${this.base}/tags/example-reference`,
          "DELETE",
          [],
        ),
      ],
    );
  }

  classifications(kind: "categories" | "tags", offset: number): Entity {
    const category = kind === "categories";
    const first = category
      ? { id: "example-notes", title: "Example notes", schema_version: 2 }
      : { id: "example-reference", name: "example-reference" };
    const second = category
      ? { id: "example-decisions", title: "Decisions", schema_version: 2 }
      : { id: "example-reviewed", name: "example-reviewed" };
    const data = offset === 0 ? first : second;
    return fixtures.entity(
      ["collection", category ? "category" : "tag"],
      category ? "Categories" : "Tags",
      { has_more: offset === 0, next_offset: offset + 1, limit: 1 },
      offset === 0
        ? [
            fixtures.link(
              `${this.base}/${kind}?offset=1&limit=1`,
              ["next"],
              "Next page",
            ),
          ]
        : [],
      this.scenario === "empty"
        ? []
        : [
            fixtures.embeddedEntity(
              [category ? "category" : "tag"],
              ["item"],
              category ? "Category" : "Tag",
              data,
              [
                fixtures.link(
                  `${this.base}/${kind}/${data.id}`,
                  ["item"],
                  category ? "Category" : "Tag",
                ),
              ],
            ),
          ],
      [category ? this.categoryCreate : this.tagCreate],
    );
  }

  manifest(): JsonObject {
    return {
      path: "examples/notes.md",
      language: "markdown",
      media_type: "text/markdown",
      size_bytes: this.source.length,
      revision: this.resourceRevision,
    };
  }
  manifests(): Entity {
    return fixtures.entity(
      ["collection", "resource-manifest"],
      "Resources",
      {
        record_id: "example",
        revision: this.resourceSetRevision,
        offset: 0,
        limit: 50,
        total: 1,
        has_more: false,
        next_offset: 1,
      },
      [],
      [
        fixtures.embeddedEntity(
          ["resource-manifest"],
          ["item"],
          "Resource",
          this.manifest(),
          [
            fixtures.link(
              `${this.base}/example/resources/content?path=examples%2Fnotes.md&expected_revision=${this.resourceRevision}`,
              ["item"],
              "Resource",
            ),
          ],
        ),
      ],
      [],
    );
  }

  sourcePage(offset: number): Entity {
    const end = Math.min(offset + 35, this.source.length);
    return fixtures.entity(
      ["command-result"],
      "RecordResourceContent",
      {
        record_id: "example",
        path: "examples/notes.md",
        language: "markdown",
        media_type: "text/markdown",
        revision: this.resourceRevision,
        offset,
        limit: 35,
        total_characters: this.source.length,
        content: this.source.slice(offset, end),
        has_more: end < this.source.length,
        next_offset: end,
      },
      end < this.source.length
        ? [
            fixtures.link(
              `${this.base}/example/resources/content?path=examples%2Fnotes.md&expected_revision=${this.resourceRevision}&offset=${end}&limit=35`,
              ["next"],
              "Next page",
            ),
          ]
        : [],
      [],
      [],
    );
  }

  initial(name: PreviewProps["initial"]): Entity {
    if (name === "record" || name === "editor" || name === "new")
      return this.record();
    if (name === "categories") return this.classifications("categories", 0);
    if (name === "category") return this.category();
    if (name === "tags") return this.classifications("tags", 0);
    if (name === "tag") return this.tag();
    if (name === "resources") return this.manifests();
    if (name === "source") return this.sourcePage(0);
    return this.collection(false);
  }

  handlers(): HttpHandler[] {
    return new RecordsPreviewHandlers(this).handlers();
  }
}
