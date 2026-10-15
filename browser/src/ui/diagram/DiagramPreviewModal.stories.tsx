import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { DiagramPreviewContent } from "./DiagramPreviewContent";
import { DiagramPreviewModal } from "./DiagramPreviewModal";

const meta = {
  component: DiagramPreviewModal,
  args: {
    onClose: fn(),
    opened: true,
    title: "Request flow",
  },
  title: "Browser/Diagrams/Full-screen preview",
} satisfies Meta<typeof DiagramPreviewModal>;

export default meta;
type Story = StoryObj<typeof meta>;

export const MermaidEmbed: Story = {
  args: {
    children: (
      <DiagramPreviewContent
        diagramId="diagram-1"
        revision={3}
        source={"flowchart LR\n  Browser --> API"}
        status="ready"
        title="Request flow"
      />
    ),
  },
};

export const Loading: Story = {
  args: {
    children: <DiagramPreviewContent status="loading" title="Request flow" />,
  },
};

export const Failure: Story = {
  args: {
    children: (
      <DiagramPreviewContent
        message="The diagram resource could not be loaded."
        onRetry={fn()}
        status="error"
      />
    ),
  },
};
