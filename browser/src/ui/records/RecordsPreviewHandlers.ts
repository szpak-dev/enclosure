import type { Entity } from "@siren-js/client";
import { delay, http, HttpResponse, type HttpHandler } from "msw";
import { sirenFixtures as fixtures } from "../../stories/SirenFixtures";
import { recordContract as contract } from "./RecordContract";

import type { RecordsPreviewData } from "./RecordsPreviewData";

export class RecordsPreviewHandlers {
  constructor(readonly data: RecordsPreviewData) {}
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
        if (
          request.method === "DELETE" &&
          this.data.scenario === "delete-success"
        ) {
          this.data.deleted = true;
          return new HttpResponse(null, { status: 204 });
        }
        if (request.method === "DELETE")
          return this.json(
            fixtures.entity(
              ["error"],
              "Deletion unavailable",
              this.data.scenario === "approval"
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
          if (this.data.scenario === "search-failure" && !this.data.recovered)
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
          return this.json(this.data.collection(true));
        }
        if (request.method === "POST" || request.method === "PUT") {
          const raw: unknown = await request.json();
          const body = contract.object(raw);
          this.data.writes(body);
          if (
            this.data.scenario === "save-failure" &&
            this.data.failurePending
          ) {
            this.data.failurePending = false;
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
                  revision: this.data.schemaRevision,
                  size_bytes: 180,
                },
                [],
                [],
                [],
              ),
            );
          if (path.includes("categories")) {
            const entity = this.data.category();
            entity.properties = {
              ...entity.properties,
              title: contract.string(body.title),
            };
            return this.json(entity);
          }
          if (path.includes("tags")) {
            const entity = this.data.tag();
            entity.properties = {
              ...entity.properties,
              name: contract.string(body.name),
            };
            return this.json(entity);
          }
          const entity = this.data.record();
          entity.properties = {
            ...entity.properties,
            title: contract.string(body.title),
            content: contract.jsonObject(body.content),
          };
          this.data.saved = { kind: "available", value: entity };
          return this.json(entity);
        }
        if (path.includes("resource-manifests")) {
          if (this.data.scenario === "loading") await delay("infinite");
          if (
            (this.data.scenario === "load-failure" && !this.data.recovered) ||
            this.data.scenario === "stale"
          ) {
            return this.json(
              fixtures.entity(
                ["error"],
                "Resources unavailable",
                {
                  detail:
                    this.data.scenario === "stale"
                      ? "Resource content changed. Reload the record before editing."
                      : "Source resources could not be loaded.",
                },
                [],
                [],
                [],
              ),
              this.data.scenario === "stale" ? 422 : 503,
            );
          }
          return this.json(this.data.manifests());
        }
        if (path.endsWith("resources/content"))
          return this.json(this.data.sourcePage(offset));
        if (path.endsWith("content-schema")) {
          const source = JSON.stringify(this.data.schema);
          return this.json(
            fixtures.entity(
              ["command-result"],
              "RecordCategoryContentSchema",
              {
                category_id: path.includes("example-decisions")
                  ? "example-decisions"
                  : "example-notes",
                schema_version: 2,
                revision: this.data.schemaRevision,
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
          const source = JSON.stringify(this.data.content);
          return this.json(
            fixtures.entity(
              ["command-result"],
              "RecordJsonContent",
              {
                record_id: "example",
                revision: this.data.revision,
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
          return this.json(this.data.classifications("categories", offset));
        if (path.endsWith("/tags"))
          return this.json(this.data.classifications("tags", offset));
        if (path.includes("/categories/")) {
          const entity = this.data.category();
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
        if (path.includes("/tags/")) return this.json(this.data.tag());
        if (path.endsWith("/example")) return this.json(this.data.record());
        return this.json(this.data.collection(false));
      }),
    ];
  }
}
