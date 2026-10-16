import type { Meta, StoryObj } from "@storybook/react-vite";
import type { Entity, Target } from "@siren-js/client";
import { expect, fn, userEvent, within } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { GuidanceRelationshipCollection } from "./GuidanceCollections";

const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  {},
  [],
  [],
  [],
);
const relationship = sirenFixtures.embeddedEntity(
  ["guidance-relationship"],
  ["item"],
  "Guidance relationship",
  {
    id: "relationship-1",
    kind: "containment",
    source_record_id: "record-1",
    target_record_id: "record-2",
  },
  [
    sirenFixtures.link("/siren/records/record-1", ["item"], "Record"),
    sirenFixtures.link("/siren/records/record-2", ["item"], "Record"),
  ],
);
const relationships = sirenFixtures.entity(
  ["collection", "guidance-relationship"],
  "Guidance relationships",
  { has_more: false, limit: 50 },
  [],
  [relationship],
  [],
);

function href(target: Target): string {
  return typeof target === "string" ? target : target.href.toString();
}

const meta = {
  component: GuidanceRelationshipCollection,
  args: {
    entity: relationships,
    onFollow: fn(),
    onLoad: fn(async (target: Target): Promise<Entity> =>
      sirenFixtures.entity(
        ["record"],
        href(target).endsWith("record-1")
          ? "Delivery lifecycle"
          : "Verification policy",
        {
          title: href(target).endsWith("record-1")
            ? "Delivery lifecycle"
            : "Verification policy",
        },
        [],
        [],
        [],
      ),
    ),
    onRefresh: fn(),
    onSubmit: fn(),
    root,
  },
  parameters: { viewport: { defaultViewport: "mobile1" } },
  title: "Browser/Projects/Guidance",
} satisfies Meta<SirenEntityProps>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Relationships: Story = {
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Containment")).toBeVisible();
    const source = await canvas.findByRole("button", {
      name: "Delivery lifecycle",
    });
    await expect(canvas.getByText("record-1")).toBeVisible();
    await expect(canvas.getByText("record-2")).toBeVisible();
    await userEvent.click(source);
    await expect(args.onFollow).toHaveBeenCalledWith(
      expect.objectContaining({ href: "/siren/records/record-1" }),
    );
  },
};
