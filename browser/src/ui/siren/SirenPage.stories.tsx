import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, within } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";
import { SirenPage } from "./SirenPage";

const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  { title: "Enclosure API" },
  [],
  [],
  [],
);

const meta = {
  component: SirenPage,
  args: {
    entity: null,
    isLoading: false,
    onFollow: fn(),
    onLoad: fn(async () => root),
    onRefresh: fn(),
    onSubmit: fn(),
    root,
  },
  title: "Browser/Siren/Page",
} satisfies Meta<typeof SirenPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Loading: Story = {
  args: {
    isLoading: true,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("status", { name: "Loading resource" }),
    ).toBeVisible();
  },
};

export const NoResourceSelected: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("No resource selected.")).toBeVisible();
  },
};
