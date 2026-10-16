import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, within } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { WorkspaceCollection } from "./WorkspaceCollection";

const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  {},
  [],
  [],
  [],
);
const workspace = sirenFixtures.embeddedEntity(
  ["workspace"],
  ["item"],
  "Workspace binding",
  {
    architecture_root: "/a/complete/architecture/root/that/remains/recoverable",
    id: "workspace-1",
    revision: 17,
    root: "/a/complete/workspace/root/that/remains/recoverable",
  },
  [
    sirenFixtures.link(
      "/siren/projects/project-1/workspaces/workspace-1",
      ["item"],
      "WorkspaceBinding",
    ),
  ],
);
const collection = sirenFixtures.entity(
  ["collection", "workspace"],
  "Workspaces",
  { has_more: false, limit: 50 },
  [],
  [workspace],
  [],
);

const meta = {
  component: WorkspaceCollection,
  args: {
    entity: collection,
    onFollow: fn(),
    onLoad: fn(),
    onRefresh: fn(),
    onSubmit: fn(),
    root,
  },
  parameters: { viewport: { defaultViewport: "mobile1" } },
  title: "Browser/Projects/Workspaces",
} satisfies Meta<SirenEntityProps>;

export default meta;
type Story = StoryObj<typeof meta>;

export const PopulatedNarrow: Story = {
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("table", { name: "Bound workspaces" }),
    ).toBeVisible();
    canvas.getByRole("link", { name: "Open" }).click();
    await expect(args.onFollow).toHaveBeenCalledWith(
      expect.objectContaining({
        href: "/siren/projects/project-1/workspaces/workspace-1",
      }),
    );
    await expect(
      canvasElement.ownerDocument.documentElement.scrollWidth,
    ).toBeLessThanOrEqual(
      canvasElement.ownerDocument.documentElement.clientWidth,
    );
  },
};
