import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, spyOn, userEvent, within } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { ArchitectureConfigurationEntity } from "./ArchitectureConfiguration";

const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  {},
  [],
  [],
  [],
);
const configuration = sirenFixtures.entity(
  ["architecture-configuration"],
  "Project architecture configuration",
  {
    boundaries_total_characters: 84,
    boundaries_yaml:
      "boundaries:\n  tags:\n    - name: application\n      description: application boundary\n",
    id: "configuration-1",
    project_id: "project-1",
    revision: "revision-1",
    shape_total_characters: 73,
    shape_yaml:
      "shape:\n  realms:\n    - name: application\n      packages:\n        - src/app\n",
  },
  [],
  [],
  [],
);

const meta = {
  component: ArchitectureConfigurationEntity,
  args: {
    entity: configuration,
    onFollow: fn(),
    onLoad: fn(),
    onRefresh: fn(),
    onSubmit: fn(),
    root,
  },
  parameters: { viewport: { defaultViewport: "mobile1" } },
  title: "Browser/Projects/Architecture configuration",
} satisfies Meta<SirenEntityProps>;

export default meta;
type Story = StoryObj<typeof meta>;

export const NarrowDocuments: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByLabelText("boundaries YAML configuration"),
    ).toBeVisible();
    await userEvent.click(canvas.getByRole("tab", { name: "Shape" }));
    await expect(
      canvas.getByLabelText("shape YAML configuration"),
    ).toBeVisible();
    spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    await userEvent.click(
      canvas.getByRole("button", { name: "Copy shape YAML" }),
    );
    await expect(
      await canvas.findByRole("button", { name: "Copied" }),
    ).toBeVisible();
  },
};
