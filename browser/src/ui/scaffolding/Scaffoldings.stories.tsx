import type { Entity, Target } from "@siren-js/client";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import {
  SirenActionExecutionProvider,
  type SirenActionExecutor,
} from "../siren/SirenActionExecution";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { ScaffoldingCollection } from "./ScaffoldingCollection";
import { ScaffoldingEntity } from "./ScaffoldingEntity";
import { TemplateManifestCollection } from "./TemplateManifestCollection";

import {
  collection,
  emptyCollection,
  href,
  loadScaffoldingSupport,
  manifests,
  renderedContent,
  rendering,
  root,
  scaffolding,
  searchResults,
  templateFirst,
  templateLast,
} from "./ScaffoldingStoryFixtures";

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
    const row = canvas.getByRole("listitem");
    const open = canvas.getByRole("link", { name: "Open scaffolding" });
    const bounds = row.getBoundingClientRect();
    await expect(
      bounds.right - open.getBoundingClientRect().right,
    ).toBeGreaterThanOrEqual(15);
    await expect(
      bounds.right - open.getBoundingClientRect().right,
    ).toBeLessThanOrEqual(17);
    await expect(open.getBoundingClientRect().left).toBeGreaterThan(
      bounds.left + bounds.width / 2,
    );

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
