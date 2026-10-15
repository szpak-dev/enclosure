import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";
import {
  DiagramOrderField,
  DiagramSortDirection,
} from "../diagram/DiagramOrderingControls";
import { SirenCollection } from "./SirenCollection";

const updatedAt = "2026-10-15T08:30:00Z";

const navigableItem = sirenFixtures.embeddedEntity(
  ["diagram-set"],
  ["item"],
  "System context",
  { id: "set-1", title: "System context", updated_at: updatedAt },
  [sirenFixtures.link("/siren/diagram-sets/set-1", ["self"], "System context")],
);
const untargetedItem = sirenFixtures.embeddedEntity(
  ["status"],
  ["item"],
  "Maintenance window",
  { id: "status-1", title: "Maintenance window" },
  [],
);
const duplicateItem = sirenFixtures.embeddedEntity(
  ["project"],
  ["item"],
  "Enclosure",
  { id: "project-2", title: "Enclosure" },
  [sirenFixtures.link("/siren/projects/project-2", ["self"], "Enclosure")],
);
const multiRelationshipItem = sirenFixtures.embeddedEntity(
  ["diagram-set"],
  ["item"],
  "System context",
  { id: "set-1", title: "System context", updated_at: updatedAt },
  [
    sirenFixtures.link("/siren/diagram-sets/set-1", ["self"], "System context"),
    sirenFixtures.link(
      "/siren/diagram-sets/set-1/diagrams",
      ["collection"],
      "Diagrams",
    ),
  ],
);
const diagramItem = sirenFixtures.embeddedEntity(
  ["diagram"],
  ["item"],
  "Request flow",
  {
    id: "diagram-1",
    kind: "flowchart-v2",
    revision: 3,
    title: "Request flow",
    updated_at: updatedAt,
  },
  [sirenFixtures.link("/siren/diagrams/diagram-1", ["self"], "Request flow")],
);
const diagramDetail = sirenFixtures.entity(
  ["diagram"],
  "Request flow",
  {
    id: "diagram-1",
    kind: "flowchart-v2",
    revision: 3,
    snapshot: { version: 1 },
    source: "flowchart LR\n  Browser --> API",
    title: "Request flow",
    updated_at: updatedAt,
  },
  [],
  [],
  [],
);

const ordering = {
  direction: DiagramSortDirection.Descending,
  has_more: true,
  limit: 50,
  next_offset: 50,
  order_by: DiagramOrderField.UpdatedAt,
};

const meta = {
  component: SirenCollection,
  args: {
    onFollow: fn(),
    onLoad: fn(async () => diagramDetail),
    onSubmit: fn(),
  },
  title: "Browser/Siren/Collection",
} satisfies Meta<typeof SirenCollection>;

export default meta;
type Story = StoryObj<typeof meta>;

export const NavigableItem: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["collection", "diagram-set"],
      "Diagram sets",
      ordering,
      [
        sirenFixtures.link(
          "/siren/diagram-sets?limit=50&order_by=updated_at&direction=desc",
          ["self"],
          "Diagram sets",
        ),
        sirenFixtures.link(
          "/siren/diagram-sets?offset=50&limit=50&order_by=updated_at&direction=desc",
          ["next"],
          "Next page",
        ),
      ],
      [navigableItem],
      [],
    ),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Diagram sets are ordered by the latest update among their contained diagrams. The second row shows that activity as relative time, with the exact ISO timestamp available on hover.",
      },
    },
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("link", { name: /System context/ }));
    await expect(args.onFollow).toHaveBeenCalledWith(
      expect.objectContaining({ href: "/siren/diagram-sets/set-1" }),
    );
  },
};

export const SortingAndContinuation: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["collection", "diagram-set"],
      "Diagram sets",
      {
        ...ordering,
        direction: DiagramSortDirection.Ascending,
        order_by: DiagramOrderField.Title,
      },
      [
        sirenFixtures.link(
          "/siren/diagram-sets?limit=50&order_by=title&direction=asc",
          ["self"],
          "Diagram sets",
        ),
        sirenFixtures.link(
          "/siren/diagram-sets?offset=50&limit=50&order_by=title&direction=asc",
          ["next"],
          "Next page",
        ),
      ],
      [navigableItem],
      [],
    ),
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    const document = within(canvasElement.ownerDocument.body);

    await userEvent.click(canvas.getByRole("combobox", { name: "Sort by" }));
    await userEvent.click(
      await document.findByRole("option", { name: "Updated" }),
    );
    await expect(args.onFollow).toHaveBeenNthCalledWith(
      1,
      "/siren/diagram-sets?limit=50&order_by=updated_at&direction=asc&offset=0",
    );

    await userEvent.click(canvas.getByRole("radio", { name: "Descending" }));
    await expect(args.onFollow).toHaveBeenNthCalledWith(
      2,
      "/siren/diagram-sets?limit=50&order_by=title&direction=desc&offset=0",
    );

    await userEvent.click(canvas.getByRole("link", { name: "Next page" }));
    await expect(args.onFollow).toHaveBeenNthCalledWith(
      3,
      expect.objectContaining({
        href: "/siren/diagram-sets?offset=50&limit=50&order_by=title&direction=asc",
      }),
    );
  },
};

export const GlobalDiagramsWithPreviewActions: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["collection", "diagram"],
      "Diagrams",
      ordering,
      [
        sirenFixtures.link(
          "/siren/diagrams?limit=50&order_by=updated_at&direction=desc",
          ["self"],
          "Diagrams",
        ),
      ],
      [diagramItem],
      [],
    ),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Global diagram rows use the shared list item, including type, relative update time with an ISO hover value, detail navigation, and a separate preview action.",
      },
    },
  },
};

export const SingleCanonicalLink: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["collection", "diagram-set"],
      "Diagram sets",
      ordering,
      [
        sirenFixtures.link(
          "/siren/diagram-sets?limit=50&order_by=updated_at&direction=desc",
          ["self"],
          "Diagram sets",
        ),
      ],
      [multiRelationshipItem],
      [],
    ),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getAllByRole("link")).toHaveLength(1);
  },
};

export const UntargetedItem: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["collection", "status"],
      "Statuses",
      { title: "Statuses" },
      [],
      [untargetedItem],
      [],
    ),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.queryByRole("link")).not.toBeInTheDocument();
    await expect(canvas.getByText("Maintenance window")).toBeVisible();
  },
};

export const AmbiguousTitles: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["collection", "project"],
      "Projects",
      { title: "Projects" },
      [],
      [
        sirenFixtures.embeddedEntity(
          ["project"],
          ["item"],
          "Enclosure",
          { id: "project-1", title: "Enclosure" },
          [
            sirenFixtures.link(
              "/siren/projects/project-1",
              ["self"],
              "Enclosure",
            ),
          ],
        ),
        duplicateItem,
      ],
      [],
    ),
  },
};
