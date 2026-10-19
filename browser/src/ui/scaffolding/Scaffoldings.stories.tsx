import type { Meta, StoryObj } from "@storybook/react-vite";
import type { Entity, Target } from "@siren-js/client";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";
import {
  SirenActionExecutionProvider,
  type SirenActionExecutor,
} from "../siren/SirenActionExecution";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { ScaffoldingCollection } from "./ScaffoldingCollection";
import { ScaffoldingEntity } from "./ScaffoldingEntity";
import { TemplateManifestCollection } from "./TemplateManifestCollection";

function href(target: Target): string {
  return typeof target === "string" ? target : target.href.toString();
}

const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  { title: "Enclosure API" },
  [sirenFixtures.link("/siren/scaffoldings", ["collection"], "Scaffoldings")],
  [],
  [],
);

const scaffoldingItem = sirenFixtures.embeddedEntity(
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

const create = sirenFixtures.action(
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
const search = sirenFixtures.action(
  "search_scaffoldings",
  "Search scaffoldings",
  "/siren/scaffoldings/name-search-results",
  "GET",
  [
    sirenFixtures.field("name", "Name", "text"),
    sirenFixtures.field("language_id", "Language", "text"),
  ],
);
const collection = sirenFixtures.entity(
  ["collection", "scaffolding"],
  "Scaffoldings",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [scaffoldingItem],
  [create, search],
);
const emptyCollection = sirenFixtures.entity(
  ["collection", "scaffolding"],
  "Scaffoldings",
  { has_more: false, limit: 50, next_offset: 0 },
  [],
  [],
  [create, search],
);
const searchResults = sirenFixtures.entity(
  ["collection", "name-search-result"],
  "ScaffoldingSummary",
  { has_more: false, limit: 20, next_offset: 1 },
  [],
  [scaffoldingItem],
  [search],
);

const update = sirenFixtures.action(
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
const render = sirenFixtures.action(
  "render_scaffolding",
  "Render a scaffolding",
  "/siren/scaffoldings/scaffolding-1/renderings",
  "POST",
  [],
);
const readRendered = sirenFixtures.action(
  "read_scaffolding_rendered_file",
  "Read rendered scaffolding content",
  "/siren/scaffoldings/scaffolding-1/rendered-file-content",
  "POST",
  [],
);
const remove = sirenFixtures.action(
  "delete_scaffolding",
  "Delete a scaffolding",
  "/siren/scaffoldings/scaffolding-1",
  "DELETE",
  [],
);
const scaffolding = sirenFixtures.entity(
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

const templateItem = sirenFixtures.embeddedEntity(
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
const manifests = sirenFixtures.entity(
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
const templateFirst = sirenFixtures.entity(
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
const templateLast = sirenFixtures.entity(
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
const rendering = sirenFixtures.entity(
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
const renderedContent = sirenFixtures.entity(
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

const loadScaffoldingSupport = fn(async (target: Target): Promise<Entity> => {
  const targetHref = href(target);
  if (targetHref.includes("template-manifests")) return manifests;
  if (targetHref.includes("offset=5")) return templateLast;
  return templateFirst;
});

const meta = {
  component: ScaffoldingCollection,
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async () => ({ kind: "empty" }));
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  args: {
    entity: collection,
    onFollow: fn(),
    onLoad: loadScaffoldingSupport,
    onRefresh: fn(),
    onSubmit: fn(),
    root,
  },
  title: "Browser/Scaffoldings",
} satisfies Meta<SirenEntityProps>;

export default meta;
type Story = StoryObj<SirenEntityProps>;

export const PopulatedCatalogue: Story = {
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("heading", { level: 1, name: "Scaffoldings" }),
    ).toBeVisible();
    await expect(
      canvas.getByText("Creates a typed Python package."),
    ).toBeVisible();
    await userEvent.click(
      canvas.getByRole("link", { name: "Open scaffolding" }),
    );
    await expect(args.onFollow).toHaveBeenCalledWith(
      expect.objectContaining({ href: "/siren/scaffoldings/scaffolding-1" }),
    );
  },
};

export const EmptyCatalogue: Story = {
  args: { entity: emptyCollection },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent(
      "No scaffolding matches",
    );
  },
};

export const SearchResultPresentation: Story = {
  args: { entity: searchResults },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("heading", {
        level: 1,
        name: "Scaffolding search results",
      }),
    ).toBeVisible();
    await expect(canvas.getByText("Python package")).toBeVisible();
  },
};

export const DetailWithHydratedUpdate: Story = {
  args: { entity: scaffolding },
  render: (args) => <ScaffoldingEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("heading", { level: 1, name: "Python package" }),
    ).toBeVisible();
    await expect(
      canvas.getByRole("button", { name: "Render a scaffolding" }),
    ).toBeVisible();
    await waitFor(() =>
      expect(
        canvas.queryByLabelText("Loading complete template specification"),
      ).not.toBeInTheDocument(),
    );
    await userEvent.click(canvas.getByRole("button", { name: "More actions" }));
    await userEvent.click(
      await within(canvasElement.ownerDocument.body).findByRole("menuitem", {
        name: "Update a scaffolding",
      }),
    );
    await expect(
      await within(canvasElement.ownerDocument.body).findByRole("dialog", {
        name: "Update a scaffolding",
      }),
    ).toBeVisible();
    await expect(
      canvas.getByRole("heading", { name: "Danger zone" }),
    ).toBeVisible();
  },
};

export const UpdateUnavailableWithoutTemplateHydration: Story = {
  args: {
    entity: scaffolding,
    onLoad: fn(async (): Promise<Entity> => {
      throw new Error("Template service unavailable");
    }),
  },
  render: (args) => <ScaffoldingEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("alert")).toHaveTextContent(
      "update form is withheld",
    );
    await expect(
      canvas.queryByRole("button", { name: "Update a scaffolding" }),
    ).not.toBeInTheDocument();
    await expect(
      canvas.getByRole("button", { name: "Render a scaffolding" }),
    ).toBeVisible();
  },
};

export const TemplateInspectionAndContinuation: Story = {
  args: {
    entity: manifests,
    onLoad: fn(async (target: Target) =>
      href(target).includes("offset=5") ? templateLast : templateFirst,
    ),
  },
  render: (args) => <TemplateManifestCollection {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(
      canvas.getByRole("button", { name: "View template" }),
    );
    const sources = await canvas.findAllByLabelText("Template source");
    await expect(sources.at(-1)).toHaveTextContent("from");
    await userEvent.click(
      canvas.getByRole("button", { name: "Load more template content" }),
    );
    await expect(
      await canvas.findByText("from typing import Any"),
    ).toBeVisible();
    await expect(
      canvas.getByText("Complete revision-pinned template loaded."),
    ).toBeVisible();
  },
};

export const TemplateReadFailure: Story = {
  args: {
    entity: manifests,
    onLoad: fn(async (): Promise<Entity> => {
      throw new Error("Template content unavailable");
    }),
  },
  render: (args) => <TemplateManifestCollection {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(
      canvas.getByRole("button", { name: "View template" }),
    );
    await expect(await canvas.findByRole("alert")).toHaveTextContent(
      "Template content unavailable",
    );
  },
};

export const RenderingAndBoundedContent: Story = {
  args: { entity: scaffolding },
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async (action) => ({
        entity:
          action.name === "render_scaffolding" ? rendering : renderedContent,
        kind: "entity",
      }));
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  render: (args) => <ScaffoldingEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Render a scaffolding" }),
    );
    const drawer = await page.findByRole("dialog", {
      name: "Render a scaffolding",
    });
    await userEvent.type(
      within(drawer).getByRole("textbox", { name: "Package name" }),
      "package",
    );
    await userEvent.click(
      within(drawer).getByRole("button", { name: "Render a scaffolding" }),
    );
    await expect(await within(drawer).findByRole("status")).toHaveTextContent(
      "Action completed",
    );
    await userEvent.click(
      within(drawer).getByRole("button", { name: "View rendered file" }),
    );
    await expect(
      await within(drawer).findByLabelText("Rendered file content"),
    ).toHaveTextContent("from typing import Any");
  },
};

export const DestructiveConfirmation: Story = {
  args: { entity: scaffolding },
  render: (args) => <ScaffoldingEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Delete a scaffolding" }),
    );
    const confirmation = await page.findByRole("dialog", {
      name: "Delete a scaffolding?",
    });
    await expect(
      within(confirmation).getByText(/permanently removes/),
    ).toBeVisible();
    await userEvent.click(
      within(confirmation).getByRole("button", { name: "Cancel" }),
    );
    await waitFor(() =>
      expect(
        page.queryByRole("dialog", { name: "Delete a scaffolding?" }),
      ).not.toBeInTheDocument(),
    );
  },
};
