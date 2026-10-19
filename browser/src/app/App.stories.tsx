import type { Meta, StoryObj } from "@storybook/react-vite";
import { delay, http, HttpResponse } from "msw";
import { expect, userEvent, within } from "storybook/test";
import { App } from "./App";

const SIREN_HEADERS = { "Content-Type": "application/vnd.siren+json" };
const rootDocument = {
  actions: [],
  class: ["api", "entry-point"],
  entities: [],
  links: [
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

const projectsDocument = {
  actions: [],
  class: ["collection", "project"],
  entities: [],
  links: [{ href: "/siren/projects", rel: ["self"], title: "Projects" }],
  properties: {},
  title: "Projects",
};

const scaffoldingsDocument = {
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

const scaffoldingDocument = {
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

const templateManifestsDocument = {
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

const templateContentDocument = {
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

const projectDocument = {
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

const updatedProjectDocument = {
  ...projectDocument,
  properties: { id: "project-1", title: "Updated project" },
  title: "Updated project",
};

const rootHandler = http.get("*/siren/", () =>
  HttpResponse.json(rootDocument, { headers: SIREN_HEADERS }),
);

const meta = {
  component: App,
  beforeEach: () => {
    window.history.replaceState(null, "", "/");
    return () => window.history.replaceState(null, "", "/");
  },
  parameters: {
    msw: {
      handlers: [rootHandler],
    },
  },
  args: {
    rootTarget: "/siren/",
  },
  title: "Browser/Application",
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

export const LoadedAndNavigable: Story = {
  parameters: {
    msw: {
      handlers: [
        rootHandler,
        http.get("*/siren/projects", () =>
          HttpResponse.json(projectsDocument, { headers: SIREN_HEADERS }),
        ),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      await canvas.findByRole("heading", { name: "Enclosure API" }),
    ).toBeVisible();
    await userEvent.click(canvas.getByRole("button", { name: "Projects" }));
    await userEvent.click(
      await canvas.findByRole("link", { name: "Projects" }),
    );
    await expect(
      await canvas.findByRole("heading", { name: "Projects" }),
    ).toBeVisible();
  },
};

export const ScaffoldingWorkflow: Story = {
  beforeEach: () => {
    window.history.replaceState(null, "", "/#/siren/scaffoldings");
  },
  parameters: {
    msw: {
      handlers: [
        rootHandler,
        http.get("*/siren/scaffoldings", () =>
          HttpResponse.json(scaffoldingsDocument, { headers: SIREN_HEADERS }),
        ),
        http.get("*/siren/scaffoldings/scaffolding-1", () =>
          HttpResponse.json(scaffoldingDocument, { headers: SIREN_HEADERS }),
        ),
        http.get("*/siren/scaffoldings/scaffolding-1/template-manifests", () =>
          HttpResponse.json(templateManifestsDocument, {
            headers: SIREN_HEADERS,
          }),
        ),
        http.get("*/siren/scaffoldings/scaffolding-1/template-content", () =>
          HttpResponse.json(templateContentDocument, {
            headers: SIREN_HEADERS,
          }),
        ),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      await canvas.findByRole("heading", { level: 1, name: "Scaffoldings" }),
    ).toBeVisible();
    await userEvent.click(
      canvas.getByRole("link", { name: "Open scaffolding" }),
    );
    await expect(
      await canvas.findByRole("heading", {
        level: 1,
        name: "Python package",
      }),
    ).toBeVisible();
    await userEvent.click(
      await canvas.findByRole("link", { name: "Browse templates" }),
    );
    await expect(
      await canvas.findByRole("heading", { level: 1, name: "Templates" }),
    ).toBeVisible();
    await userEvent.click(
      canvas.getByRole("button", { name: "View template" }),
    );
    await expect(
      await canvas.findByText("from typing import Any"),
    ).toBeVisible();
  },
};

export const RootLoading: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/siren/", async () => {
          await delay("infinite");
          return HttpResponse.json(rootDocument, { headers: SIREN_HEADERS });
        }),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      await canvas.findByRole("status", { name: "Loading resource" }),
    ).toBeVisible();
  },
};

export const RootFailureAndRecovery: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get(
          "*/siren/",
          () =>
            HttpResponse.json(
              {
                actions: [],
                class: ["error"],
                entities: [],
                links: [],
                properties: { detail: "Navigation service unavailable" },
                title: "Navigation unavailable",
              },
              { headers: SIREN_HEADERS, status: 503 },
            ),
          { once: true },
        ),
        rootHandler,
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("alert")).toHaveTextContent(
      "Navigation service unavailable",
    );
    await userEvent.click(canvas.getByRole("button", { name: "Retry" }));
    await expect(
      await canvas.findByRole("heading", { name: "Enclosure API" }),
    ).toBeVisible();
  },
};

export const ResourceLoading: Story = {
  beforeEach: () => {
    window.history.replaceState(null, "", "/#/siren/projects");
  },
  parameters: {
    msw: {
      handlers: [
        rootHandler,
        http.get("*/siren/projects", async () => {
          await delay("infinite");
          return HttpResponse.json(projectsDocument, {
            headers: SIREN_HEADERS,
          });
        }),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      await canvas.findByRole("status", { name: "Loading resource" }),
    ).toBeVisible();
  },
};

export const ResourceFailureAndRecovery: Story = {
  beforeEach: () => {
    window.history.replaceState(null, "", "/#/siren/projects");
  },
  parameters: {
    msw: {
      handlers: [
        rootHandler,
        http.get(
          "*/siren/projects",
          () =>
            HttpResponse.json(
              {
                actions: [],
                class: ["error"],
                entities: [],
                links: [],
                properties: {
                  detail: "Projects are temporarily unavailable",
                },
                title: "Projects unavailable",
              },
              { headers: SIREN_HEADERS, status: 503 },
            ),
          { once: true },
        ),
        http.get("*/siren/projects", () =>
          HttpResponse.json(projectsDocument, { headers: SIREN_HEADERS }),
        ),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("alert")).toHaveTextContent(
      "Projects are temporarily unavailable",
    );
    await userEvent.click(canvas.getByRole("button", { name: "Retry" }));
    await expect(
      await canvas.findByRole("heading", { name: "Projects" }),
    ).toBeVisible();
  },
};

export const ActiveDeepLink: Story = {
  beforeEach: () => {
    window.history.replaceState(null, "", "/#/siren/projects");
  },
  parameters: {
    msw: {
      handlers: [
        rootHandler,
        http.get("*/siren/projects", () =>
          HttpResponse.json(projectsDocument, { headers: SIREN_HEADERS }),
        ),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      await canvas.findByRole("heading", { name: "Projects" }),
    ).toBeVisible();
    await expect(
      await canvas.findByRole("link", { name: "Projects" }),
    ).toHaveAttribute("aria-current", "page");
  },
};

export const NarrowNavigation: Story = {
  parameters: {
    msw: {
      handlers: [
        rootHandler,
        http.get("*/siren/projects", () =>
          HttpResponse.json(projectsDocument, { headers: SIREN_HEADERS }),
        ),
      ],
    },
    viewport: {
      defaultViewport: "mobile1",
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      await canvas.findByRole("heading", { name: "Enclosure API" }),
    ).toBeVisible();
    const toggle = await canvas.findByRole("button", {
      name: "Toggle navigation",
    });
    await userEvent.click(toggle);
    await userEvent.click(canvas.getByRole("button", { name: "Projects" }));
    await userEvent.click(
      await canvas.findByRole("link", { name: "Projects" }),
    );
    await expect(
      await canvas.findByRole("heading", { name: "Projects" }),
    ).toBeVisible();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
  },
};

export const ActionValidationFailure: Story = {
  beforeEach: () => {
    window.history.replaceState(null, "", "/#/siren/projects/project-1");
  },
  parameters: {
    msw: {
      handlers: [
        rootHandler,
        http.get("*/siren/projects/project-1", () =>
          HttpResponse.json(projectDocument, { headers: SIREN_HEADERS }),
        ),
        http.patch("*/siren/projects/project-1", () =>
          HttpResponse.json(
            {
              actions: [],
              class: ["error"],
              entities: [],
              links: [],
              properties: {
                detail: [
                  {
                    loc: ["body", "title"],
                    msg: "Title must contain at least two characters.",
                  },
                ],
              },
              title: "Validation failed",
            },
            { headers: SIREN_HEADERS, status: 422 },
          ),
        ),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const title = await canvas.findByRole("textbox", { name: "Project title" });
    await userEvent.clear(title);
    await userEvent.type(title, "X");
    await userEvent.click(
      canvas.getByRole("button", { name: "Rename project" }),
    );
    await expect(await canvas.findByRole("alert")).toHaveTextContent(
      "Title must contain at least two characters.",
    );
  },
};

export const ActionConflict: Story = {
  beforeEach: () => {
    window.history.replaceState(null, "", "/#/siren/projects/project-1");
  },
  parameters: {
    msw: {
      handlers: [
        rootHandler,
        http.get("*/siren/projects/project-1", () =>
          HttpResponse.json(projectDocument, { headers: SIREN_HEADERS }),
        ),
        http.patch("*/siren/projects/project-1", () =>
          HttpResponse.json(
            {
              actions: [],
              class: ["error"],
              entities: [],
              links: [],
              properties: { detail: "The project changed before submission." },
              title: "Revision conflict",
            },
            { headers: SIREN_HEADERS, status: 409 },
          ),
        ),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(
      await canvas.findByRole("button", { name: "Rename project" }),
    );
    await expect(await canvas.findByRole("alert")).toHaveTextContent(
      "The project changed before submission.",
    );
  },
};

export const ActionSuccess: Story = {
  beforeEach: () => {
    window.history.replaceState(null, "", "/#/siren/projects/project-1");
  },
  parameters: {
    msw: {
      handlers: [
        rootHandler,
        http.get("*/siren/projects/project-1", () =>
          HttpResponse.json(projectDocument, { headers: SIREN_HEADERS }),
        ),
        http.patch("*/siren/projects/project-1", async () => {
          await delay(100);
          return HttpResponse.json(updatedProjectDocument, {
            headers: SIREN_HEADERS,
          });
        }),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const title = await canvas.findByRole("textbox", { name: "Project title" });
    await userEvent.clear(title);
    await userEvent.type(title, "Updated project");
    const submit = canvas.getByRole("button", { name: "Rename project" });
    await userEvent.click(submit);
    await expect(submit).toBeDisabled();
    await expect(
      await canvas.findByRole("heading", { name: "Updated project" }),
    ).toBeVisible();
  },
};
