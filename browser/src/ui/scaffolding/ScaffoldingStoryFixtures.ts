import type { Entity, Target } from "@siren-js/client";
import { fn } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";

export function href(target: Target): string {
  return typeof target === "string" ? target : target.href.toString();
}

export const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  { title: "Enclosure API" },
  [sirenFixtures.link("/siren/scaffoldings", ["collection"], "Scaffoldings")],
  [],
  [],
);

export const scaffoldingItem = sirenFixtures.embeddedEntity(
  ["scaffolding"],
  ["item"],
  "Python package",
  {
    description: "Creates a typed Python package.",
    id: "scaffolding-1",
    language_id: "python",
    name: "Python package",
  },
  [
    sirenFixtures.link(
      "/siren/scaffoldings/scaffolding-1",
      ["item"],
      "Scaffolding",
    ),
  ],
);

export const create = sirenFixtures.action(
  "create_scaffolding",
  "Create a scaffolding",
  "/siren/scaffoldings",
  "POST",
  [
    sirenFixtures.field("language_id", "Language", "text"),
    sirenFixtures.field("name", "Name", "text"),
    sirenFixtures.field("description", "Description", "text"),
  ],
);
export const search = sirenFixtures.action(
  "search_scaffoldings",
  "Search scaffoldings",
  "/siren/scaffoldings/name-search-results",
  "GET",
  [
    sirenFixtures.field("name", "Name", "text"),
    sirenFixtures.field("language_id", "Language", "text"),
  ],
);
export const collection = sirenFixtures.entity(
  ["collection", "scaffolding"],
  "Scaffoldings",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [scaffoldingItem],
  [create, search],
);
export const emptyCollection = sirenFixtures.entity(
  ["collection", "scaffolding"],
  "Scaffoldings",
  { has_more: false, limit: 50, next_offset: 0 },
  [],
  [],
  [create, search],
);
export const searchResults = sirenFixtures.entity(
  ["collection", "name-search-result"],
  "ScaffoldingSummary",
  { has_more: false, limit: 20, next_offset: 1 },
  [],
  [scaffoldingItem],
  [search],
);

export const update = sirenFixtures.action(
  "update_scaffolding",
  "Update a scaffolding",
  "/siren/scaffoldings/scaffolding-1",
  "PUT",
  [
    sirenFixtures.field("language_id", "Language", "text"),
    sirenFixtures.field("name", "Name", "text"),
    sirenFixtures.field("description", "Description", "text"),
  ],
);
export const render = sirenFixtures.action(
  "render_scaffolding",
  "Render a scaffolding",
  "/siren/scaffoldings/scaffolding-1/renderings",
  "POST",
  [],
);
export const readRendered = sirenFixtures.action(
  "read_scaffolding_rendered_file",
  "Read rendered scaffolding content",
  "/siren/scaffoldings/scaffolding-1/rendered-file-content",
  "POST",
  [],
);
export const remove = sirenFixtures.action(
  "delete_scaffolding",
  "Delete a scaffolding",
  "/siren/scaffoldings/scaffolding-1",
  "DELETE",
  [],
);
export const scaffolding = sirenFixtures.entity(
  ["scaffolding"],
  "Python package",
  {
    description: "Creates a typed Python package.",
    id: "scaffolding-1",
    language_id: "python",
    name: "Python package",
    spec: {
      language: "python",
      templates: [
        {
          path: "src/{{ package_name }}/__init__.py",
          revision: "template-revision-1",
          size_bytes: 38,
          write_mode: "overwrite",
        },
      ],
      variables: [{ name: "package_name", type: "string" }],
    },
    template_count: 1,
    templates_revision: "templates-revision-1",
  },
  [
    sirenFixtures.link(
      "/siren/scaffoldings/scaffolding-1/template-manifests",
      ["collection"],
      "TemplateManifest",
    ),
  ],
  [],
  [update, render, readRendered, remove],
);

export const templateItem = sirenFixtures.embeddedEntity(
  ["template-manifest"],
  ["item"],
  "Template manifest",
  {
    path: "src/{{ package_name }}/__init__.py",
    revision: "template-revision-1",
    size_bytes: 38,
    write_mode: "overwrite",
  },
  [
    sirenFixtures.link(
      "/siren/scaffoldings/scaffolding-1/template-content?path=src%2Fpackage%2F__init__.py&expected_revision=template-revision-1&offset=0&limit=20",
      ["item"],
      "TemplateContent",
    ),
  ],
);
export const manifests = sirenFixtures.entity(
  ["collection", "template-manifest"],
  "Template manifests",
  {
    has_more: false,
    limit: 50,
    next_offset: 1,
    revision: "templates-revision-1",
    scaffolding_id: "scaffolding-1",
  },
  [],
  [templateItem],
  [],
);
export const templateFirst = sirenFixtures.entity(
  ["template-content"],
  "Template content",
  {
    content: "from ",
    has_more: true,
    limit: 20,
    next_offset: 5,
    path: "src/{{ package_name }}/__init__.py",
    revision: "template-revision-1",
    total_characters: 17,
    write_mode: "overwrite",
  },
  [
    sirenFixtures.link(
      "/siren/scaffoldings/scaffolding-1/template-content?offset=5&limit=20",
      ["next"],
      "Next",
    ),
  ],
  [],
  [],
);
export const templateLast = sirenFixtures.entity(
  ["template-content"],
  "Template content",
  {
    content: "typing import Any",
    has_more: false,
    limit: 20,
    next_offset: 17,
    path: "src/{{ package_name }}/__init__.py",
    revision: "template-revision-1",
    total_characters: 17,
    write_mode: "overwrite",
  },
  [],
  [],
  [],
);
export const rendering = sirenFixtures.entity(
  ["command-result"],
  "Rendered scaffolding",
  {
    has_more: false,
    items: [
      {
        overwrite: true,
        path: "src/package/__init__.py",
        preview: "from typing import Any",
        revision: "rendered-revision-1",
        size_bytes: 22,
      },
    ],
    limit: 50,
    next_offset: 1,
  },
  [],
  [],
  [],
);
export const renderedContent = sirenFixtures.entity(
  ["rendered-file-content"],
  "Rendered file content",
  {
    content: "from typing import Any",
    has_more: false,
    limit: 1000,
    next_offset: 22,
    path: "src/package/__init__.py",
    revision: "rendered-revision-1",
    total_characters: 22,
  },
  [],
  [],
  [],
);

export const loadScaffoldingSupport = fn(
  async (target: Target): Promise<Entity> => {
    const targetHref = href(target);
    if (targetHref.includes("template-manifests")) return manifests;
    if (targetHref.includes("offset=5")) return templateLast;
    return templateFirst;
  },
);
