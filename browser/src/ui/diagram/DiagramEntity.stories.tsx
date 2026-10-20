import { MantineProvider } from "@mantine/core";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";
import { DiagramEntity } from "./DiagramEntity";

const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  { title: "Enclosure API" },
  [],
  [],
  [],
);

const meta = {
  component: DiagramEntity,
  args: {
    onFollow: fn(),
    onLoad: fn(),
    onRefresh: fn(),
    onSubmit: fn(),
    root,
  },
  title: "Browser/Diagrams/Detail",
} satisfies Meta<typeof DiagramEntity>;

export default meta;
type Story = StoryObj<typeof meta>;

async function expectRenderedPreview(
  canvasElement: HTMLElement,
  title: string,
) {
  const canvas = within(canvasElement);
  const document = within(canvasElement.ownerDocument.body);
  await userEvent.click(
    canvas.getByRole("button", { name: "Preview diagram" }),
  );
  const preview = await document.findByRole(
    "img",
    { name: `${title} Mermaid preview` },
    { timeout: 10_000 },
  );
  await expect(preview.querySelector("svg")).not.toBeNull();
  await expect(document.queryByRole("alert")).not.toBeInTheDocument();
  await waitFor(() =>
    expect(
      document.getByRole("toolbar", { name: "Diagram zoom controls" }),
    ).toBeVisible(),
  );
  return preview;
}

export const PreviewAction: Story = {
  args: {
    entity: sirenFixtures.entity(
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
    ),
  },
  play: async ({ canvasElement }) => {
    const preview = await expectRenderedPreview(canvasElement, "Request flow");
    const document = within(canvasElement.ownerDocument.body);
    const toolbar = document.getByRole("toolbar", {
      name: "Diagram zoom controls",
    });
    const center = document.getByRole("button", {
      name: "Center and fit diagram",
    });
    const previewBounds = preview.getBoundingClientRect();
    const toolbarBounds = toolbar.getBoundingClientRect();
    const centerBounds = center.getBoundingClientRect();
    await expect(toolbarBounds.right).toBeLessThanOrEqual(previewBounds.right);
    await expect(toolbarBounds.left).toBeGreaterThan(
      previewBounds.left + previewBounds.width / 2,
    );
    await expect(centerBounds.left).toBeGreaterThanOrEqual(previewBounds.left);
    await expect(centerBounds.right).toBeLessThan(
      previewBounds.left + previewBounds.width / 2,
    );
    await userEvent.click(document.getByRole("button", { name: "Zoom in" }));
    await expect(document.getByLabelText("Zoom level")).toHaveTextContent(
      "125%",
    );
    await userEvent.click(
      document.getByRole("button", { name: "Center and fit diagram" }),
    );
    await expect(document.getByLabelText("Zoom level")).toHaveTextContent(
      "100%",
    );
    await expect(document.queryByRole("iframe")).not.toBeInTheDocument();
  },
};

export const SequenceSemicolon: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["diagram"],
      "Sequence compatibility",
      {
        id: "diagram-sequence",
        kind: "sequenceDiagram",
        revision: 3,
        snapshot: { version: 1 },
        source: `sequenceDiagram
participant requester@{ "type": "participant" } as Requester
participant worker@{ "type": "participant" } as Worker
requester->>worker: Decide#59; then continue`,
        title: "Sequence compatibility",
        updated_at: "2026-10-20T08:30:00Z",
      },
      [],
      [],
      [],
    ),
  },
  play: async ({ canvasElement }) => {
    await expectRenderedPreview(canvasElement, "Sequence compatibility");
  },
};

export const StateSemicolon: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["diagram"],
      "State compatibility",
      {
        id: "diagram-state",
        kind: "stateDiagram-v2",
        revision: 3,
        snapshot: { version: 1 },
        source: `stateDiagram-v2
direction TB
state "Ready" as s_v_ready
note right of s_v_ready : "Wait; then continue"`,
        title: "State compatibility",
        updated_at: "2026-10-20T08:30:00Z",
      },
      [],
      [],
      [],
    ),
  },
  play: async ({ canvasElement }) => {
    await expectRenderedPreview(canvasElement, "State compatibility");
  },
};

export const EntityPathIdentifiers: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["diagram"],
      "Entity compatibility",
      {
        id: "diagram-entity",
        kind: "erDiagram",
        revision: 3,
        snapshot: { version: 1 },
        source: `erDiagram
e_h_4eba3053ba4e379a4577f296cff1b109["Example source"] {
}
e_h_5f5cccf7ed824d1e6b42acc66b690662["Example target"] {
}
e_h_4eba3053ba4e379a4577f296cff1b109 ||--|| e_h_5f5cccf7ed824d1e6b42acc66b690662 : "uses"`,
        title: "Entity compatibility",
        updated_at: "2026-10-20T08:30:00Z",
      },
      [],
      [],
      [],
    ),
  },
  play: async ({ canvasElement }) => {
    await expectRenderedPreview(canvasElement, "Entity compatibility");
  },
};

export const InvalidSource: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["diagram"],
      "Invalid diagram",
      {
        id: "diagram-3",
        kind: "flowchart-v2",
        revision: 1,
        snapshot: { version: 1 },
        source: "flowchart LR\n  Browser -->",
        title: "Invalid diagram",
        updated_at: "2026-10-15T08:30:00Z",
      },
      [],
      [],
      [],
    ),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const document = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Preview diagram" }),
    );
    await expect(
      await document.findByRole("alert", undefined, { timeout: 10_000 }),
    ).toHaveTextContent("Unable to render Mermaid preview");
    await expect(document.queryByRole("img")).not.toBeInTheDocument();
  },
};

export const DarkMode: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["diagram"],
      "Dark tree",
      {
        id: "diagram-dark-tree",
        kind: "treeView-beta",
        revision: 1,
        snapshot: { version: 1 },
        source: "treeView-beta\nroot/\n  child.ts",
        title: "Dark tree",
        updated_at: "2026-10-20T08:30:00Z",
      },
      [],
      [],
      [],
    ),
  },
  decorators: [
    (Story) => (
      <MantineProvider forceColorScheme="dark">
        <Story />
      </MantineProvider>
    ),
  ],
  play: async ({ canvasElement }) => {
    const preview = await expectRenderedPreview(canvasElement, "Dark tree");
    const svg = preview.querySelector("svg");
    const label = preview.querySelector(".treeView-node-label");
    const line = preview.querySelector(".treeView-node-line");
    await expect(svg).not.toBeNull();
    await expect(label).not.toBeNull();
    await expect(line).not.toBeNull();
    if (!label || !line)
      throw new Error("Dark tree did not expose its visible labels and lines.");
    await expect(getComputedStyle(label).fill).toBe("rgb(193, 194, 197)");
    await expect(getComputedStyle(line).stroke).toBe("rgb(193, 194, 197)");
  },
};

export const EmptySource: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["diagram"],
      "Empty diagram",
      {
        id: "diagram-2",
        kind: "flowchart-v2",
        revision: 1,
        snapshot: { version: 1 },
        source: "",
        title: "Empty diagram",
        updated_at: "2026-10-15T08:30:00Z",
      },
      [],
      [],
      [],
    ),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const document = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Preview diagram" }),
    );
    await expect(
      await document.findByRole("dialog", { name: "Empty diagram preview" }),
    ).toBeInTheDocument();
    await expect(
      document.getByText("Diagram has no source"),
    ).toBeInTheDocument();
  },
};
