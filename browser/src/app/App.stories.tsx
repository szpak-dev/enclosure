import type { Meta, StoryObj } from "@storybook/react-vite";
import { delay, http, HttpResponse } from "msw";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { App } from "./App";

import {
  projectDocument,
  projectsDocument,
  rootDocument,
  rootHandler,
  scaffoldingDocument,
  scaffoldingsDocument,
  SIREN_HEADERS,
  templateContentDocument,
  templateManifestsDocument,
  updatedProjectDocument,
} from "./AppStoryFixtures";

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

const composedCollections = [
  { path: "projects", kind: "project", title: "Projects" },
  { path: "diagram-sets", kind: "diagram-set", title: "Diagram sets" },
  { path: "scaffoldings", kind: "scaffolding", title: "Scaffoldings" },
  { path: "records", kind: "record", title: "Records" },
  { path: "languages", kind: "language", title: "Languages" },
];

export const FiveApplicationJourney: Story = {
  parameters: {
    msw: {
      handlers: [
        rootHandler,
        ...composedCollections.map(({ path, kind, title }) =>
          http.get(`*/siren/${path}`, () =>
            HttpResponse.json(
              {
                actions: [],
                class: ["collection", kind],
                entities: [],
                links: [{ href: `/siren/${path}`, rel: ["self"], title }],
                properties: {
                  has_more: false,
                  limit: 50,
                  next_offset: 0,
                  order_by: "updated_at",
                  direction: "desc",
                },
                title,
              },
              { headers: SIREN_HEADERS },
            ),
          ),
        ),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByRole("heading", { name: "Enclosure API" });
    for (const { path, title } of composedCollections) {
      const group = title;
      await userEvent.click(canvas.getByRole("button", { name: group }));
      const link = await canvas.findByRole("link", {
        name: title,
      });
      await userEvent.click(link);
      await waitFor(() => expect(window.location.hash).toBe(`#/siren/${path}`));
      await expect(
        await canvas.findByRole("heading", { name: title }),
      ).toBeVisible();
      await expect(link).toHaveAttribute("aria-current", "page");
      await expect(canvas.getAllByRole("link", { name: title })).toHaveLength(
        1,
      );
    }
    window.history.back();
    await expect(
      await canvas.findByRole("heading", { name: "Records" }),
    ).toBeVisible();
    window.history.forward();
    await expect(
      await canvas.findByRole("heading", { name: "Languages" }),
    ).toBeVisible();
  },
};
