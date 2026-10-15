import type { Meta, StoryObj } from "@storybook/react-vite";
import { delay, http, HttpResponse } from "msw";
import { userEvent, within } from "storybook/test";
import { App } from "./App";

const SIREN_HEADERS = { "Content-Type": "application/vnd.siren+json" };
let rootAttempts = 0;
let resourceAttempts = 0;

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

const meta = {
  component: App,
  parameters: {
    msw: {
      handlers: [
        http.get("*/siren/", () =>
          HttpResponse.json(rootDocument, { headers: SIREN_HEADERS }),
        ),
      ],
    },
  },
  args: {
    rootTarget: "/siren/",
  },
  title: "Browser/Application",
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Loaded: Story = {};

export const Loading: Story = {
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
};

export const RootFailure: Story = {
  beforeEach: () => {
    rootAttempts = 0;
  },
  parameters: {
    msw: {
      handlers: [
        http.get("*/siren/", () => {
          rootAttempts += 1;
          return rootAttempts === 1
            ? HttpResponse.json(
                { detail: "Navigation service unavailable" },
                { status: 503 },
              )
            : HttpResponse.json(rootDocument, { headers: SIREN_HEADERS });
        }),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Retry" }));
    await canvas.findByRole(
      "heading",
      { name: "Enclosure API" },
      { timeout: 3000 },
    );
  },
};

export const ResourceFailure: Story = {
  beforeEach: () => {
    resourceAttempts = 0;
    window.history.replaceState(null, "", "/#/siren/projects");
    return () => window.history.replaceState(null, "", "/");
  },
  parameters: {
    msw: {
      handlers: [
        http.get("*/siren/", () =>
          HttpResponse.json(rootDocument, { headers: SIREN_HEADERS }),
        ),
        http.get("*/siren/projects", () => {
          resourceAttempts += 1;
          return resourceAttempts === 1
            ? HttpResponse.json(
                { detail: "Projects are temporarily unavailable" },
                { status: 503 },
              )
            : HttpResponse.json(projectsDocument, {
                headers: SIREN_HEADERS,
              });
        }),
      ],
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Retry" }));
    await canvas.findByRole("heading", { name: "Projects" }, { timeout: 3000 });
  },
};

export const NarrowNavigation: Story = {
  parameters: {
    viewport: {
      defaultViewport: "mobile1",
    },
  },
};
