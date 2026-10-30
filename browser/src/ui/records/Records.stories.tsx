import { Alert, Button, Stack } from "@mantine/core";
import type { Meta, StoryObj } from "@storybook/react-vite";
import type { Action, Entity, Target } from "@siren-js/client";
import { http, HttpResponse, delay, type HttpHandler } from "msw";
import { Component, type ReactNode } from "react";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import { SirenClient } from "../../client/SirenClient";
import { sirenFixtures as fixtures } from "../../stories/SirenFixtures";
import { SirenActionExecutionProvider } from "../siren/SirenActionExecution";
import { SirenPage } from "../siren/SirenPage";
import {
  recordContract as contract,
  type Available,
  type JsonObject,
} from "./RecordContract";
import { RecordEditor } from "./RecordEditor";

type PreviewState =
  | "normal"
  | "empty"
  | "historical"
  | "load-failure"
  | "loading"
  | "stale"
  | "protected"
  | "approval"
  | "search-empty"
  | "search-failure"
  | "save-failure"
  | "delete-success";
type PreviewProps = {
  initial:
    | "records"
    | "record"
    | "categories"
    | "category"
    | "tags"
    | "tag"
    | "resources"
    | "source"
    | "editor"
    | "new";
  scenario: PreviewState;
};

class RecordsPreviewData {
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
  private saved: Available<Entity> = { kind: "unavailable" };
  readonly writes = fn<(body: object) => void>();
  private failurePending = true;
  private deleted = false;
  private recovered = false;

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
  private readonly categoryCreate = fixtures.action(
    "create_record_category",
    "Create a record category",
    `${this.base}/categories`,
    "POST",
    [fixtures.field("title", "Title", "text")],
  );
  private readonly tagCreate = fixtures.action(
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

  private classifications(kind: "categories" | "tags", offset: number): Entity {
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

  private manifest(): JsonObject {
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

  private json(entity: Entity, status: number = 200): Response {
    return HttpResponse.json(entity, {
      status,
      headers: { "Content-Type": "application/vnd.siren+json" },
    });
  }

  handlers(): HttpHandler[] {
    return [
      http.all(/\/siren\/(records|languages)/, async ({ request }) => {
        const url = new URL(request.url);
        const path = url.pathname;
        const offset = Number(url.searchParams.get("offset"));
        if (request.method === "DELETE" && this.scenario === "delete-success") {
          this.deleted = true;
          return new HttpResponse(null, { status: 204 });
        }
        if (request.method === "DELETE")
          return this.json(
            fixtures.entity(
              ["error"],
              "Deletion unavailable",
              this.scenario === "approval"
                ? {
                    reason_code: "destructive_approval_required",
                    detail:
                      "Approve this exact deletion through an authorized security client.",
                    approval_request_id: "example-request",
                  }
                : {
                    detail:
                      "This record or classification is in use and cannot be deleted.",
                  },
              [],
              [],
              [],
            ),
            409,
          );
        if (path.endsWith("search-results")) {
          if (this.scenario === "search-failure" && !this.recovered)
            return this.json(
              fixtures.entity(
                ["error"],
                "Search unavailable",
                { detail: "Example search service unavailable." },
                [],
                [],
                [],
              ),
              503,
            );
          return this.json(this.collection(true));
        }
        if (request.method === "POST" || request.method === "PUT") {
          const raw: unknown = await request.json();
          const body = contract.object(raw);
          this.writes(body);
          if (this.scenario === "save-failure" && this.failurePending) {
            this.failurePending = false;
            return this.json(
              fixtures.entity(
                ["error"],
                "Save unavailable",
                {
                  detail:
                    "Example temporary failure. Retry your unchanged draft.",
                },
                [],
                [],
                [],
              ),
              503,
            );
          }
          if (path.endsWith("content-schema"))
            return this.json(
              fixtures.entity(
                ["command-result"],
                "Schema saved",
                {
                  category_id: "example-notes",
                  version: 3,
                  revision: this.schemaRevision,
                  size_bytes: 180,
                },
                [],
                [],
                [],
              ),
            );
          if (path.includes("categories")) {
            const entity = this.category();
            entity.properties = {
              ...entity.properties,
              title: contract.string(body.title),
            };
            return this.json(entity);
          }
          if (path.includes("tags")) {
            const entity = this.tag();
            entity.properties = {
              ...entity.properties,
              name: contract.string(body.name),
            };
            return this.json(entity);
          }
          const entity = this.record();
          entity.properties = {
            ...entity.properties,
            title: contract.string(body.title),
            content: contract.jsonObject(body.content),
          };
          this.saved = { kind: "available", value: entity };
          return this.json(entity);
        }
        if (path.includes("resource-manifests")) {
          if (this.scenario === "loading") await delay("infinite");
          if (
            (this.scenario === "load-failure" && !this.recovered) ||
            this.scenario === "stale"
          ) {
            return this.json(
              fixtures.entity(
                ["error"],
                "Resources unavailable",
                {
                  detail:
                    this.scenario === "stale"
                      ? "Resource content changed. Reload the record before editing."
                      : "Source resources could not be loaded.",
                },
                [],
                [],
                [],
              ),
              this.scenario === "stale" ? 422 : 503,
            );
          }
          return this.json(this.manifests());
        }
        if (path.endsWith("resources/content"))
          return this.json(this.sourcePage(offset));
        if (path.endsWith("content-schema")) {
          const source = JSON.stringify(this.schema);
          return this.json(
            fixtures.entity(
              ["command-result"],
              "RecordCategoryContentSchema",
              {
                category_id: path.includes("example-decisions")
                  ? "example-decisions"
                  : "example-notes",
                schema_version: 2,
                revision: this.schemaRevision,
                offset: 0,
                limit: source.length,
                total_characters: source.length,
                content: source,
                has_more: false,
                next_offset: source.length,
              },
              [],
              [],
              [],
            ),
          );
        }
        if (path.endsWith("/content")) {
          const source = JSON.stringify(this.content);
          return this.json(
            fixtures.entity(
              ["command-result"],
              "RecordJsonContent",
              {
                record_id: "example",
                revision: this.revision,
                offset: 0,
                limit: source.length,
                total_characters: source.length,
                content: source,
                has_more: false,
                next_offset: source.length,
              },
              [],
              [],
              [],
            ),
          );
        }
        if (path.endsWith("/languages"))
          return this.json(
            fixtures.entity(
              ["collection", "language"],
              "Languages",
              {},
              [],
              [
                fixtures.embeddedEntity(
                  ["language"],
                  ["item"],
                  "Markdown",
                  { id: "markdown", name: "Markdown" },
                  [
                    fixtures.link(
                      "/siren/languages/markdown",
                      ["self"],
                      "Language",
                    ),
                  ],
                ),
              ],
              [],
            ),
          );
        if (path.endsWith("/categories"))
          return this.json(this.classifications("categories", offset));
        if (path.endsWith("/tags"))
          return this.json(this.classifications("tags", offset));
        if (path.includes("/categories/")) {
          const entity = this.category();
          if (path.endsWith("example-decisions")) {
            for (const action of entity.actions)
              Object.assign(action, {
                href: contract
                  .href(action)
                  .replace("example-notes", "example-decisions"),
              });
            entity.properties = {
              ...entity.properties,
              id: "example-decisions",
              title: "Decisions",
            };
          }
          return this.json(entity);
        }
        if (path.includes("/tags/")) return this.json(this.tag());
        if (path.endsWith("/example")) return this.json(this.record());
        return this.json(this.collection(false));
      }),
    ];
  }
}

type PreviewSession = {
  entity: Entity;
  loading: boolean;
  error: string;
  editor: boolean;
};
class RecordsPreview extends Component<PreviewProps, PreviewSession> {
  private readonly data = new RecordsPreviewData(this.props.scenario);
  private readonly client = new SirenClient();
  state: PreviewSession = {
    entity: this.data.initial(this.props.initial),
    loading: false,
    error: "",
    editor: this.props.initial === "editor" || this.props.initial === "new",
  };
  private readonly targets: Record<PreviewProps["initial"], string> = {
    records: "/siren/records",
    record: "/siren/records/example",
    editor: "/siren/records/example",
    new: "/siren/records",
    categories: "/siren/records/categories",
    category: "/siren/records/categories/example-notes",
    tags: "/siren/records/tags",
    tag: "/siren/records/tags/example-reference",
    resources: "/siren/records/example/resource-manifests",
    source: "/siren/records/example/resources/content",
  };
  private target: Target = this.targets[this.props.initial];
  private async follow(target: Target): Promise<void> {
    this.target = target;
    this.setState({ loading: true, error: "" });
    try {
      this.setState({ entity: await this.client.get(target), loading: false });
    } catch (reason) {
      this.setState({ error: contract.message(reason), loading: false });
    }
  }
  render(): ReactNode {
    return (
      <SirenActionExecutionProvider
        execute={async (action, values) => {
          const result = await this.client.execute(action, values);
          return result === null
            ? { kind: "empty" }
            : { kind: "entity", entity: result };
        }}
      >
        <Stack component="main" p="md">
          {this.state.error ? (
            <Alert color="red" title="Unable to load resource">
              <Stack>
                {this.state.error}
                <Button onClick={() => void this.follow(this.target)}>
                  Retry
                </Button>
              </Stack>
            </Alert>
          ) : (
            <SirenPage
              entity={this.state.entity}
              root={this.data.root()}
              isLoading={this.state.loading}
              onLoad={(target) => this.client.get(target)}
              onFollow={(target) => void this.follow(target)}
              onRefresh={() => void this.follow(this.target)}
              onSubmit={(action: Action, values: Record<string, unknown>) => {
                void this.client.execute(action, values).then((entity) => {
                  if (entity !== null) this.setState({ entity });
                });
              }}
            />
          )}
          {this.state.editor ? (
            <RecordEditor
              action={
                this.props.initial === "new"
                  ? this.data.create
                  : this.data.update
              }
              source={
                this.props.initial === "new"
                  ? { kind: "unavailable" }
                  : { kind: "available", value: "/siren/records/example" }
              }
              root={this.data.root()}
              onLoad={(target) => this.client.get(target)}
              onClose={() => this.setState({ editor: false })}
              onSaved={(entity) => this.setState({ entity, editor: false })}
            />
          ) : (
            <></>
          )}
        </Stack>
      </SirenActionExecutionProvider>
    );
  }
}

const normal = new RecordsPreviewData("normal");
const meta = {
  title: "Browser/Records",
  component: RecordsPreview,
  args: { initial: "records", scenario: "normal" },
  parameters: { msw: { handlers: normal.handlers() } },
  beforeEach: () => normal.reset(),
} satisfies Meta<typeof RecordsPreview>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Records: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(
      canvas.getByRole("textbox", { name: /Describe/ }),
      "example decisions",
    );
    await userEvent.click(canvas.getByRole("button", { name: "Search" }));
    await expect(await canvas.findByText(/Results for/)).toBeVisible();
    await userEvent.click(canvas.getByRole("button", { name: /Clear/ }));
    await expect(canvas.getByRole("textbox", { name: /Describe/ })).toHaveValue(
      "",
    );
    await userEvent.click(
      canvas.getByRole("link", { name: "Open Example decisions" }),
    );
    await expect(
      await canvas.findByRole("heading", { name: "Example decisions" }),
    ).toBeVisible();
  },
};
export const EmptyRecords: Story = {
  play: async ({ canvasElement }) => {
    await expect(
      within(canvasElement).getByText("No records yet"),
    ).toBeVisible();
  },
  args: { scenario: "empty" },
  parameters: { msw: { handlers: new RecordsPreviewData("empty").handlers() } },
};
export const RecordDetails: Story = { args: { initial: "record" } };
export const CreateRecord: Story = {
  args: { initial: "new" },
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.type(
      await body.findByRole("textbox", { name: "Title" }),
      "Example new record",
    );
    await userEvent.click(body.getByRole("combobox", { name: "Category" }));
    await userEvent.click(
      await body.findByRole("option", { name: "Decisions" }),
    );
    await userEvent.click(body.getByRole("combobox", { name: "Tags" }));
    await userEvent.click(
      await body.findByRole("option", { name: "example-reviewed" }),
    );
    await userEvent.keyboard("{Escape}");
    await userEvent.type(
      await body.findByRole("textbox", { name: /Summary/ }),
      "Example content",
    );
    await userEvent.click(body.getByRole("button", { name: "Create record" }));
    await waitFor(() =>
      expect(normal.writes).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Example new record",
          category_id: "example-decisions",
          tag_ids: ["example-reviewed"],
          resources: [],
          content: { summary: "Example content" },
        }),
      ),
    );
    await expect(
      await body.findByRole("heading", { name: "Example new record" }),
    ).toBeVisible();
  },
};
export const EditRecord: Story = {
  args: { initial: "editor" },
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    const title = await body.findByRole("textbox", {
      name: "Title",
    });
    await waitFor(() =>
      expect(body.getByRole("button", { name: "Save changes" })).toBeEnabled(),
    );
    await userEvent.clear(title);
    await userEvent.click(body.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(title).toHaveFocus());
    await expect(normal.writes).not.toHaveBeenCalled();
    await userEvent.type(title, "Example revised record");
    await userEvent.click(body.getByRole("button", { name: "Cancel" }));
    await waitFor(() =>
      expect(
        body.getByRole("dialog", { name: "Discard unsaved changes?" }),
      ).toBeVisible(),
    );
    await userEvent.click(body.getByRole("button", { name: "Keep editing" }));
    await userEvent.click(body.getByRole("button", { name: "Save changes" }));
    await waitFor(() =>
      expect(normal.writes).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Example revised record",
          category_id: "example-notes",
          tag_ids: ["example-reference", "example-reviewed"],
          content: normal.content,
          resources: [
            {
              path: "examples/notes.md",
              language: "markdown",
              content: normal.source,
            },
          ],
        }),
      ),
    );
    await expect(
      await body.findByRole("heading", { name: "Example revised record" }),
    ).toBeVisible();
  },
};
export const HistoricalSchema: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await expect(
      await body.findByText("JSON editing for this schema version"),
    ).toBeVisible();
    await expect(
      body.getByRole("textbox", { name: "Content JSON" }),
    ).toHaveValue(JSON.stringify(normal.content, null, 2));
    await expect(
      body.queryByRole("radio", { name: "Fields" }),
    ).not.toBeInTheDocument();
  },
  args: { initial: "editor", scenario: "historical" },
  parameters: {
    msw: { handlers: new RecordsPreviewData("historical").handlers() },
  },
};
export const PreparingEditor: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await expect(
      await body.findByRole("status", { name: "Preparing editor" }),
    ).toBeVisible();
    await expect(
      body.queryByRole("button", { name: "Save changes" }),
    ).not.toBeInTheDocument();
  },
  args: { initial: "editor", scenario: "loading" },
  parameters: {
    msw: { handlers: new RecordsPreviewData("loading").handlers() },
  },
};
const loadFailureData = new RecordsPreviewData("load-failure");
export const ResourceLoadFailure: Story = {
  beforeEach: () => loadFailureData.reset(),
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await expect(await body.findByText("Editor unavailable")).toBeVisible();
    await expect(
      body.queryByRole("button", { name: "Save changes" }),
    ).not.toBeInTheDocument();
    loadFailureData.recover();
    await userEvent.click(
      body.getByRole("button", { name: "Reload and retry" }),
    );
    await waitFor(() =>
      expect(body.getByRole("button", { name: "Save changes" })).toBeEnabled(),
    );
  },
  args: { initial: "editor", scenario: "load-failure" },
  parameters: {
    msw: { handlers: loadFailureData.handlers() },
  },
};
export const StaleResources: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await expect(
      await body.findByText(/Resource content changed/),
    ).toBeVisible();
    await expect(
      body.queryByRole("button", { name: "Save changes" }),
    ).not.toBeInTheDocument();
  },
  args: { initial: "editor", scenario: "stale" },
  parameters: { msw: { handlers: new RecordsPreviewData("stale").handlers() } },
};
export const Categories: Story = {
  args: { initial: "categories" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("link", { name: "Next page" }));
    await expect(
      await canvas.findByRole("button", { name: "Open Decisions" }),
    ).toBeVisible();
    await userEvent.click(
      canvas.getByRole("button", { name: "Open Decisions" }),
    );
    await expect(
      await canvas.findByRole("heading", { name: "Decisions" }),
    ).toBeVisible();
  },
};
export const CategoryDetails: Story = {
  args: { initial: "category" },
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      await body.findByRole("button", { name: "More actions" }),
    );
    await userEvent.click(
      await body.findByRole("menuitem", { name: "Edit schema" }),
    );
    const dialog = await body.findByRole("dialog", { name: "Edit schema" });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Edit schema" }),
    );
    await expect(
      await within(dialog).findByText("Schema v3 saved"),
    ).toBeVisible();
    await expect(
      within(dialog).getByText(
        "Existing records keep their assigned schema version.",
      ),
    ).toBeVisible();
    await expect(normal.writes).toHaveBeenCalledWith({
      content_schema: normal.schema,
    });
  },
};
export const Tags: Story = { args: { initial: "tags" } };
export const TagDetails: Story = {
  args: { initial: "tag" },
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(body.getByRole("button", { name: "Rename tag" }));
    const dialog = await body.findByRole("dialog", { name: "Rename tag" });
    const field = within(dialog).getByRole("textbox", { name: "Name" });
    await userEvent.clear(field);
    await userEvent.type(field, "example-renamed");
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Rename tag" }),
    );
    await expect(
      await within(dialog).findByText("example-renamed"),
    ).toBeVisible();
    await expect(normal.writes).toHaveBeenCalledWith({
      name: "example-renamed",
    });
  },
};
export const Resources: Story = { args: { initial: "resources" } };
export const SourcePages: Story = {
  args: { initial: "source" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText(/Characters 0–35/)).toBeVisible();
    await userEvent.click(canvas.getByRole("link", { name: /Next/ }));
    await expect(await canvas.findByText(/Characters 35–70/)).toBeVisible();
    await userEvent.click(canvas.getByRole("link", { name: /Next/ }));
    await expect(await canvas.findByText(/Characters 70–/)).toBeVisible();
    await expect(
      canvas.queryByRole("link", { name: /Next/ }),
    ).not.toBeInTheDocument();
  },
};
export const ProtectedRecord: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(body.getByRole("button", { name: "Delete record" }));
    await userEvent.click(
      await body.findByRole("button", { name: "Continue" }),
    );
    const dialog = await body.findByRole("dialog", { name: "Delete record" });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Delete record" }),
    );
    await expect(
      await body.findByText("Action could not proceed", { exact: true }),
    ).toBeVisible();
    await expect(
      body.getByRole("heading", { name: "Example decisions", hidden: true }),
    ).toBeInTheDocument();
  },
  args: { initial: "record", scenario: "protected" },
  parameters: {
    msw: { handlers: new RecordsPreviewData("protected").handlers() },
  },
};
export const ApprovalRequired: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(body.getByRole("button", { name: "Delete record" }));
    await userEvent.click(
      await body.findByRole("button", { name: "Continue" }),
    );
    const dialog = await body.findByRole("dialog", { name: "Delete record" });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Delete record" }),
    );
    await expect(
      await body.findByText("One-time approval required", { exact: true }),
    ).toBeVisible();
    await expect(
      body.getByRole("heading", { name: "Example decisions", hidden: true }),
    ).toBeInTheDocument();
  },
  args: { initial: "record", scenario: "approval" },
  parameters: {
    msw: { handlers: new RecordsPreviewData("approval").handlers() },
  },
};

const retryData = new RecordsPreviewData("save-failure");
export const SaveFailure: Story = {
  args: { initial: "editor", scenario: "save-failure" },
  parameters: { msw: { handlers: retryData.handlers() } },
  beforeEach: () => retryData.reset(),
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    const title = await body.findByRole("textbox", {
      name: "Title",
    });
    await waitFor(() =>
      expect(body.getByRole("button", { name: "Save changes" })).toBeEnabled(),
    );
    await userEvent.clear(title);
    await userEvent.type(title, "Example preserved draft");
    await userEvent.click(body.getByRole("button", { name: "Save changes" }));
    await expect(
      await body.findByText(/Example temporary failure/),
    ).toBeVisible();
    await expect(title).toHaveValue("Example preserved draft");
    await userEvent.click(body.getByRole("button", { name: "Save changes" }));
    await expect(
      await body.findByRole("heading", { name: "Example preserved draft" }),
    ).toBeVisible();
    await expect(retryData.writes).toHaveBeenCalledTimes(2);
    await expect(retryData.writes.mock.calls[0]).toEqual(
      retryData.writes.mock.calls[1],
    );
  },
};

const deleteData = new RecordsPreviewData("delete-success");
export const DeleteRecord: Story = {
  args: { initial: "record", scenario: "delete-success" },
  parameters: { msw: { handlers: deleteData.handlers() } },
  beforeEach: () => deleteData.reset(),
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(body.getByRole("button", { name: "Delete record" }));
    await userEvent.click(
      await body.findByRole("button", { name: "Continue" }),
    );
    const dialog = await body.findByRole("dialog", { name: "Delete record" });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Delete record" }),
    );
    await expect(
      await within(canvasElement).findByText("No records yet"),
    ).toBeVisible();
  },
};

export const EmptySearch: Story = {
  args: { scenario: "search-empty" },
  parameters: {
    msw: { handlers: new RecordsPreviewData("search-empty").handlers() },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(
      canvas.getByRole("textbox", { name: /Describe/ }),
      "example missing record",
    );
    await userEvent.click(canvas.getByRole("button", { name: "Search" }));
    await expect(await canvas.findByText("No matching records")).toBeVisible();
    await userEvent.click(canvas.getByRole("button", { name: /Clear/ }));
    await expect(
      canvas.getByRole("link", { name: "Open Example decisions" }),
    ).toBeVisible();
  },
};
const searchFailureData = new RecordsPreviewData("search-failure");
export const SearchFailure: Story = {
  args: { scenario: "search-failure" },
  parameters: { msw: { handlers: searchFailureData.handlers() } },
  beforeEach: () => searchFailureData.reset(),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const query = canvas.getByRole("textbox", { name: /Describe/ });
    await userEvent.type(query, "example decisions");
    await userEvent.click(canvas.getByRole("button", { name: "Search" }));
    await expect(
      await canvas.findByText(/Example search service unavailable/),
    ).toBeVisible();
    await expect(query).toHaveValue("example decisions");
    searchFailureData.recover();
    await userEvent.click(canvas.getByRole("button", { name: "Retry search" }));
    await expect(await canvas.findByText(/Results for/)).toBeVisible();
    await expect(
      canvas.getByRole("link", { name: "Open Example decisions" }),
    ).toBeVisible();
  },
};
