import type { Entity, Target } from "@siren-js/client";
import { Box } from "@mantine/core";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";
import { DiagramCollection } from "./DiagramCollection";
import {
  DiagramOrderField,
  DiagramSortDirection,
} from "./DiagramOrderingControls";

const summary = sirenFixtures.embeddedEntity(
  ["diagram"],
  ["item"],
  "Request flow",
  {
    id: "diagram-1",
    kind: "flowchart-v2",
    revision: 3,
    title: "Request flow",
    updated_at: "2026-10-15T08:30:00Z",
  },
  [sirenFixtures.link("/siren/diagrams/diagram-1", ["self"], "Request flow")],
);
const sequenceSummary = sirenFixtures.embeddedEntity(
  ["diagram"],
  ["item"],
  "Command sequence",
  {
    id: "diagram-2",
    kind: "sequenceDiagram",
    revision: 1,
    title: "Command sequence",
    updated_at: "2026-10-14T16:20:00Z",
  },
  [
    sirenFixtures.link(
      "/siren/diagrams/diagram-2",
      ["self"],
      "Command sequence",
    ),
  ],
);
const detail: Entity = sirenFixtures.entity(
  ["diagram"],
  "Request flow",
  {
    id: "diagram-1",
    kind: "flowchart-v2",
    revision: 3,
    snapshot: { version: 1 },
    source: "flowchart LR\n  Browser --> API",
    title: "Request flow",
    updated_at: "2026-10-15T08:30:00Z",
  },
  [],
  [],
  [],
);
const sequenceDetail: Entity = sirenFixtures.entity(
  ["diagram"],
  "Command sequence",
  {
    id: "diagram-2",
    kind: "sequenceDiagram",
    revision: 1,
    snapshot: { version: 1 },
    source: "sequenceDiagram\n  Browser->>API: Apply command",
    title: "Command sequence",
    updated_at: "2026-10-14T16:20:00Z",
  },
  [],
  [],
  [],
);

const meta = {
  component: DiagramCollection,
  args: {
    collection: sirenFixtures.entity(
      ["collection", "diagram"],
      "Diagrams",
      {
        direction: DiagramSortDirection.Descending,
        has_more: true,
        limit: 50,
        next_offset: 50,
        order_by: DiagramOrderField.UpdatedAt,
      },
      [
        sirenFixtures.link(
          "/siren/diagram-sets/set-1/diagrams?limit=50&order_by=updated_at&direction=desc",
          ["self"],
          "Diagrams",
        ),
        sirenFixtures.link(
          "/siren/diagram-sets/set-1/diagrams?offset=50&limit=50&order_by=updated_at&direction=desc",
          ["next"],
          "Next page",
        ),
      ],
      [summary, sequenceSummary],
      [],
    ),
    onFollow: fn(),
    onLoad: fn(async (target) =>
      target.href.toString().endsWith("diagram-2") ? sequenceDetail : detail,
    ),
  },
  title: "Browser/Diagrams/Collection",
} satisfies Meta<typeof DiagramCollection>;

export default meta;
type Story = StoryObj<typeof meta>;

export const NavigableListWithPreviewActions: Story = {
  parameters: {
    docs: {
      description: {
        story:
          "Each row shows the diagram type and relative update time on its second line. Hovering the update time exposes the exact ISO timestamp.",
      },
    },
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    const document = within(canvasElement.ownerDocument.body);

    await userEvent.click(
      canvas.getByRole("button", { name: "Preview Request flow" }),
    );
    await document.findByRole("dialog", { name: "Request flow preview" });
    await expect(args.onLoad).toHaveBeenCalledWith(
      expect.objectContaining({ href: "/siren/diagrams/diagram-1" }),
    );
  },
};

export const TitleAscending: Story = {
  args: {
    collection: sirenFixtures.entity(
      ["collection", "diagram"],
      "Diagrams",
      {
        direction: DiagramSortDirection.Ascending,
        has_more: false,
        limit: 50,
        next_offset: 1,
        order_by: DiagramOrderField.Title,
      },
      [
        sirenFixtures.link(
          "/siren/diagram-sets/set-1/diagrams?limit=50&order_by=title&direction=asc",
          ["self"],
          "Diagrams",
        ),
      ],
      [summary],
      [],
    ),
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("radio", { name: "Descending" }));
    await expect(args.onFollow).toHaveBeenCalledWith(
      "/siren/diagram-sets/set-1/diagrams?limit=50&order_by=title&direction=desc&offset=0",
    );
  },
};

export const DownloadFailure: Story = {
  args: {
    onLoad: fn(async (_target: Target): Promise<Entity> => {
      throw new Error("Example diagram unavailable");
    }),
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(
      canvas.getByRole("button", { name: "Download Request flow as SVG" }),
    );
    const page = within(canvasElement.ownerDocument.body);
    await expect(await page.findByRole("alert")).toHaveTextContent(
      "Example diagram unavailable",
    );
    await waitFor(() =>
      expect(
        page.getByRole("button", { name: "Retry download" }),
      ).toBeVisible(),
    );
    await expect(args.onFollow).not.toHaveBeenCalled();
    await expect(
      page.queryByRole("dialog", { name: "Request flow preview" }),
    ).not.toBeInTheDocument();
  },
};

export const DownloadInProgress: Story = {
  args: { onLoad: fn((_target: Target) => new Promise<Entity>(() => {})) },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(
      canvas.getByRole("button", { name: "Download Request flow as SVG" }),
    );
    await expect(canvas.getByRole("status")).toHaveTextContent(
      "Preparing Request flow SVG",
    );
    await expect(
      canvas.getByRole("button", { name: "Download Request flow as SVG" }),
    ).toBeDisabled();
    await expect(args.onLoad).toHaveBeenCalledTimes(1);
  },
};

export const NarrowListActions: Story = {
  decorators: [
    (Story) => (
      <Box w={360} maw="100%">
        <Story />
      </Box>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const list = canvas.getByRole("list", { name: "Diagrams" });
    const download = canvas.getByRole("button", {
      name: "Download Request flow as SVG",
    });
    const preview = canvas.getByRole("button", {
      name: "Preview Request flow",
    });
    const downloadBounds = download.getBoundingClientRect();
    const previewBounds = preview.getBoundingClientRect();
    await expect(
      Math.abs(downloadBounds.right - list.getBoundingClientRect().right),
    ).toBeLessThanOrEqual(1);
    await expect(previewBounds.right).toBeLessThanOrEqual(downloadBounds.left);
    await expect(
      canvas
        .getByRole("button", { name: "Download Command sequence as SVG" })
        .getBoundingClientRect().right,
    ).toBe(downloadBounds.right);
    await expect(download.closest("a")).toBeNull();
    await expect(
      canvas.getAllByRole("link", { name: /Request flow/ }),
    ).toHaveLength(1);
  },
};
