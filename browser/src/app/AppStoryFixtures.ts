import { http, HttpResponse } from "msw";

export const SIREN_HEADERS = { "Content-Type": "application/vnd.siren+json" };
export const rootDocument = {
  actions: [],
  class: ["api", "entry-point"],
  entities: [],
  links: [
    { href: "/siren/records", rel: ["collection"], title: "Records" },
    { href: "/siren/languages", rel: ["collection"], title: "Languages" },
    { href: "/siren/", rel: ["self"], title: "Enclosure API" },
    {
      href: "/siren/projects",
      rel: ["collection"],
      title: "Projects",
    },
    {
      href: "/siren/diagram-sets",
      rel: ["collection"],
      title: "Diagram sets",
    },
    {
      href: "/siren/scaffoldings",
      rel: ["collection"],
      title: "Scaffoldings",
    },
  ],
  properties: { title: "Enclosure API" },
  title: "Enclosure API",
};

export const projectsDocument = {
  actions: [],
  class: ["collection", "project"],
  entities: [],
  links: [{ href: "/siren/projects", rel: ["self"], title: "Projects" }],
  properties: {},
  title: "Projects",
};

export const scaffoldingsDocument = {
  actions: [],
  class: ["collection", "scaffolding"],
  entities: [
    {
      class: ["scaffolding"],
      entities: [],
      links: [
        {
          href: "/siren/scaffoldings/scaffolding-1",
          rel: ["item"],
          title: "Scaffolding",
        },
      ],
      properties: {
        description: "Creates a typed Python package.",
        id: "scaffolding-1",
        language_id: "python",
        name: "Python package",
      },
      rel: ["item"],
      title: "Python package",
    },
  ],
  links: [
    { href: "/siren/scaffoldings", rel: ["self"], title: "Scaffoldings" },
  ],
  properties: { has_more: false, limit: 50, next_offset: 1 },
  title: "Scaffoldings",
};

export const scaffoldingDocument = {
  actions: [],
  class: ["scaffolding"],
  entities: [],
  links: [
    {
      href: "/siren/scaffoldings/scaffolding-1",
      rel: ["self"],
      title: "Python package",
    },
    {
      href: "/siren/scaffoldings/scaffolding-1/template-manifests",
      rel: ["collection"],
      title: "TemplateManifest",
    },
  ],
  properties: {
    description: "Creates a typed Python package.",
    id: "scaffolding-1",
    language_id: "python",
    name: "Python package",
    spec: {
      language: "python",
      templates: [
        {
          path: "src/package/__init__.py",
          revision: "template-revision-1",
          size_bytes: 22,
          write_mode: "overwrite",
        },
      ],
      variables: [],
    },
    template_count: 1,
    templates_revision: "templates-revision-1",
  },
  title: "Python package",
};

export const templateManifestsDocument = {
  actions: [],
  class: ["collection", "template-manifest"],
  entities: [
    {
      class: ["template-manifest"],
      entities: [],
      links: [
        {
          href: "/siren/scaffoldings/scaffolding-1/template-content?path=src%2Fpackage%2F__init__.py&expected_revision=template-revision-1&offset=0&limit=1000",
          rel: ["item"],
          title: "TemplateContent",
        },
      ],
      properties: {
        path: "src/package/__init__.py",
        revision: "template-revision-1",
        size_bytes: 22,
        write_mode: "overwrite",
      },
      rel: ["item"],
      title: "Template manifest",
    },
  ],
  links: [],
  properties: {
    has_more: false,
    limit: 50,
    next_offset: 1,
    revision: "templates-revision-1",
    scaffolding_id: "scaffolding-1",
  },
  title: "Template manifests",
};

export const templateContentDocument = {
  actions: [],
  class: ["template-content"],
  entities: [],
  links: [],
  properties: {
    content: "from typing import Any",
    has_more: false,
    limit: 1000,
    next_offset: 22,
    path: "src/package/__init__.py",
    revision: "template-revision-1",
    total_characters: 22,
    write_mode: "overwrite",
  },
  title: "Template content",
};

export const projectDocument = {
  actions: [
    {
      fields: [{ name: "title", title: "Project title", type: "text" }],
      href: "/siren/projects/project-1",
      method: "PATCH",
      name: "rename-project",
      title: "Rename project",
      type: "application/json",
    },
  ],
  class: ["example-resource"],
  entities: [],
  links: [
    {
      href: "/siren/projects/project-1",
      rel: ["self"],
      title: "Example project",
    },
  ],
  properties: { id: "project-1", title: "Example project" },
  title: "Example project",
};

export const updatedProjectDocument = {
  ...projectDocument,
  properties: { id: "project-1", title: "Updated project" },
  title: "Updated project",
};

export const rootHandler = http.get("*/siren/", () =>
  HttpResponse.json(rootDocument, { headers: SIREN_HEADERS }),
);
