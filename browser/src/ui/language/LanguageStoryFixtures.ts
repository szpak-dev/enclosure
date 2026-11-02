import type { Entity } from "@siren-js/client";
import { delay, http, HttpResponse, type HttpHandler } from "msw";
import { sirenFixtures as fixtures } from "../../stories/SirenFixtures";

export type LanguageDocument = {
  id: string;
  name: string;
  aliases: string[];
  source_extensions: string[];
};
export type Scenario =
  | "refresh"
  | "invalid-text"
  | "normal"
  | "empty"
  | "loading"
  | "failure"
  | "malformed"
  | "unavailable"
  | "action-only"
  | "related"
  | "pagination";

export class LanguagePreviewData {
  private requests = 0;
  readonly languages: LanguageDocument[] = [
    {
      id: "markdown",
      name: "Markdown",
      aliases: [],
      source_extensions: [".md"],
    },
    {
      id: "mermaid",
      name: "Mermaid",
      aliases: [],
      source_extensions: [".mermaid", ".mmd"],
    },
    { id: "php", name: "PHP", aliases: [], source_extensions: [".php"] },
    {
      id: "python",
      name: "Python",
      aliases: ["py"],
      source_extensions: [".py"],
    },
    {
      id: "typescript",
      name: "TypeScript",
      aliases: ["ts"],
      source_extensions: [".tsx", ".ts", ".jsx", ".js"],
    },
    {
      id: "yaml",
      name: "Yaml",
      aliases: [],
      source_extensions: [".yml", ".yaml"],
    },
    {
      id: "example-language",
      name: "Example language",
      aliases: [],
      source_extensions: [],
    },
  ];
  constructor(private readonly scenario: Scenario) {}

  open(path: string): void {
    this.requests = 0;
    window.history.replaceState({}, "", `#${path}`);
  }

  root(): Entity {
    return fixtures.entity(
      ["api", "entry-point"],
      "Enclosure API",
      {},
      [
        fixtures.link("/siren/", ["self"], "Enclosure API"),
        fixtures.link("/siren/languages", ["collection"], "Languages"),
      ],
      [],
      [],
    );
  }

  detail(language: LanguageDocument): Entity {
    const entity = fixtures.entity(
      ["language"],
      "Language",
      language,
      [fixtures.link(`/siren/languages/${language.id}`, ["self"], "Language")],
      [],
      [
        fixtures.action(
          "get_language",
          "Get a language",
          `/siren/languages/${language.id}`,
          "GET",
          [],
        ),
      ],
    );
    if (this.scenario === "refresh" && this.requests > 1)
      entity.properties = { ...language, name: "Example refreshed language" };
    if (this.scenario === "unavailable") {
      entity.links = [];
      entity.actions = [];
    }
    if (this.scenario === "related" && language.id === "python")
      entity.links.push(
        fixtures.link("/siren/languages/typescript", ["related"], "TypeScript"),
      );
    return entity;
  }

  collection(offset: number): Entity {
    const catalog = this.languages.slice(0, 6);
    const languages =
      this.scenario === "empty"
        ? []
        : this.scenario === "pagination"
          ? catalog.slice(offset, offset + 2)
          : catalog;
    const entities = languages.map((language) => {
      const item = fixtures.embeddedEntity(
        ["language"],
        ["item"],
        language.name,
        language,
        [
          fixtures.link(
            `/siren/languages/${language.id}`,
            ["self"],
            language.name,
          ),
        ],
      );
      item.actions = [
        fixtures.action(
          "get_language",
          "Get a language",
          `/siren/languages/${language.id}`,
          "GET",
          [],
        ),
      ];
      if (this.scenario === "unavailable") {
        item.links = [];
        item.actions = [];
      }
      if (this.scenario === "action-only") item.links = [];
      return item;
    });
    const links = [fixtures.link("/siren/languages", ["self"], "Language")];
    if (this.scenario === "pagination" && offset + 2 < catalog.length)
      links.push(
        fixtures.link(
          `/siren/languages?offset=${offset + 2}`,
          ["next"],
          "Next page",
        ),
      );
    if (this.scenario === "pagination" && offset > 0)
      links.push(
        fixtures.link(
          `/siren/languages?offset=${offset - 2}`,
          ["previous"],
          "Previous page",
        ),
      );
    return fixtures.entity(
      ["collection", "language"],
      "Language",
      {},
      links,
      entities,
      [
        fixtures.action(
          "find_languages",
          "List languages",
          "/siren/languages",
          "GET",
          [],
        ),
      ],
    );
  }

  private json(entity: Entity, status: number = 200): Response {
    return HttpResponse.json(entity, {
      status,
      headers: { "Content-Type": "application/vnd.siren+json" },
    });
  }

  handlers(): HttpHandler[] {
    return [
      http.get("*/siren/", () => this.json(this.root())),
      http.get(
        /\/siren\/languages(?:\/[^/?]+)?(?:\?.*)?$/,
        async ({ request }) => {
          this.requests += 1;
          if (this.scenario === "loading") await delay("infinite");
          if (this.scenario === "failure" && this.requests === 1)
            return this.json(
              fixtures.entity(
                ["error"],
                "Languages unavailable",
                {
                  detail:
                    "Example language service is temporarily unavailable. Try again.",
                },
                [],
                [],
                [],
              ),
              503,
            );
          const url = new URL(request.url);
          const id = url.pathname.slice(url.pathname.lastIndexOf("/") + 1);
          const language = this.languages.find((item) => item.id === id);
          const entity = language
            ? this.detail(language)
            : this.collection(Number(url.searchParams.get("offset")));
          if (this.scenario === "malformed" && this.requests === 1)
            entity.properties = { id: "python", name: "Python" };
          if (this.scenario === "invalid-text" && this.requests === 1)
            entity.properties = {
              id: "python",
              name: 42,
              aliases: [],
              source_extensions: [".py"],
            };
          return this.json(entity);
        },
      ),
    ];
  }
}
