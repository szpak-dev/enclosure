import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { ColorSchemeControl } from "./ColorSchemeControl";

const meta = {
  component: ColorSchemeControl,
  beforeEach: () => {
    window.localStorage.removeItem("enclosure-color-scheme");
  },
  title: "Browser/Application/Color scheme",
} satisfies Meta<typeof ColorSchemeControl>;

export default meta;
type Story = StoryObj<typeof meta>;

export const PersistedChoice: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);

    await userEvent.click(
      canvas.getByRole("button", { name: /^Color scheme:/ }),
    );
    await userEvent.click(await page.findByText("Dark"));

    await expect(
      canvas.getByRole("button", { name: "Color scheme: Dark" }),
    ).toBeVisible();
    await expect(window.localStorage.getItem("enclosure-color-scheme")).toBe(
      "dark",
    );
  },
};
