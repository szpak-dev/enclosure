import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
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
