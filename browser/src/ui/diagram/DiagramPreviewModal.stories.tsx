import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { DiagramPreviewContent } from "./DiagramPreviewContent";
import { DiagramPreviewModal } from "./DiagramPreviewModal";

const retry = fn();

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
  play: async ({ args, canvasElement }) => {
    const page = within(canvasElement.ownerDocument.body);
    const image = await page.findByRole(
      "img",
      { name: "Request flow Mermaid preview" },
      { timeout: 15000 },
    );
    await expect(image.querySelector("svg")).not.toBeNull();
    await userEvent.click(page.getByRole("button", { name: "Zoom in" }));
    await expect(page.getByLabelText("Zoom level")).toHaveTextContent("125%");
    await userEvent.click(page.getByRole("button", { name: "Zoom out" }));
    await expect(page.getByLabelText("Zoom level")).toHaveTextContent("100%");
    image.focus();
    const beforePan = image.querySelector("svg")!.getBoundingClientRect();
    await userEvent.keyboard("{ArrowRight}");
    await expect(image.querySelector("svg")!.getBoundingClientRect().x).toBe(
      beforePan.x - 40,
    );
    await userEvent.keyboard("+".repeat(20));
    await expect(page.getByLabelText("Zoom level")).toHaveTextContent("1200%");
    await expect(page.getByRole("button", { name: "Zoom in" })).toBeDisabled();
    await userEvent.keyboard("-".repeat(30));
    await expect(page.getByLabelText("Zoom level")).toHaveTextContent("20%");
    await expect(page.getByRole("button", { name: "Zoom out" })).toBeDisabled();
    await userEvent.click(
      page.getByRole("button", { name: "Center and fit diagram" }),
    );
    await expect(page.getByLabelText("Zoom level")).toHaveTextContent("100%");
    await expect(image.querySelector("svg")!.getBoundingClientRect().x).toBe(
      beforePan.x,
    );
    await userEvent.click(
      page.getByRole("button", { name: "Close Request flow preview" }),
    );
    await expect(args.onClose).toHaveBeenCalledTimes(1);
  },
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
  play: async ({ canvasElement }) => {
    const page = within(canvasElement.ownerDocument.body);
    await expect(await page.findByRole("status")).toHaveTextContent(
      "Loading Request flow",
    );
    await expect(page.queryByRole("img")).not.toBeInTheDocument();
  },
  args: {
    children: <DiagramPreviewContent status="loading" title="Request flow" />,
  },
};

export const Failure: Story = {
  play: async ({ canvasElement }) => {
    const page = within(canvasElement.ownerDocument.body);
    await expect(await page.findByRole("alert")).toHaveTextContent(
      "The diagram resource could not be loaded.",
    );
    await userEvent.click(page.getByRole("button", { name: "Retry" }));
    await expect(retry).toHaveBeenCalledTimes(1);
  },
  args: {
    children: (
      <DiagramPreviewContent
        message="The diagram resource could not be loaded."
        onRetry={retry}
        status="error"
      />
    ),
  },
};
