import type { Entity } from "@siren-js/client";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { sirenFixtures as fixtures } from "../../stories/SirenFixtures";
import { DiagramSetEntity } from "./DiagramSetEntity";

const target = fixtures.link(
  "/example-diagrams",
  ["collection"],
  "Example diagrams",
);
const empty = fixtures.entity(
  ["collection", "diagram"],
  "Example diagrams",
  {
    direction: "desc",
    order_by: "updated_at",
    limit: 50,
    next_offset: 0,
    has_more: false,
  },
  [fixtures.link("/example-diagrams", ["self"], "Example diagrams")],
  [],
  [],
);
const recoveryLoad = fn(async () => empty);
const meta = {
  title: "Browser/Diagrams/Gallery",
  component: DiagramSetEntity,
  args: {
    entity: fixtures.entity(
      ["diagram-set"],
      "Example set",
      { title: "Example set", description: "Example diagrams" },
      [target],
      [],
      [],
    ),
    root: fixtures.entity(["api"], "Example API", {}, [], [], []),
    onLoad: fn(async () => empty),
    onFollow: fn(),
    onRefresh: fn(),
    onSubmit: fn(),
  },
} satisfies Meta<typeof DiagramSetEntity>;
export default meta;
type Story = StoryObj<typeof meta>;
export const MissingRelationship: Story = {
  args: {
    entity: fixtures.entity(
      ["diagram-set"],
      "Example set",
      { title: "Example set" },
      [],
      [],
      [],
    ),
  },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent(
      "does not advertise a collection",
    );
  },
};
export const InvalidOrdering: Story = {
  args: {
    onLoad: fn(async () =>
      fixtures.entity(
        ["example-unordered"],
        "Example diagrams",
        {},
        [],
        [],
        [],
      ),
    ),
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByRole("alert"),
    ).toHaveTextContent("ordering is unavailable");
  },
};
export const Loading: Story = {
  args: { onLoad: fn(() => new Promise<Entity>(() => {})) },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByRole("status"),
    ).toHaveTextContent("Loading diagrams");
  },
};
export const Recovery: Story = {
  beforeEach: () => {
    recoveryLoad.mockRejectedValueOnce(
      new Error("Example collection unavailable"),
    );
  },
  args: { onLoad: recoveryLoad },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("alert")).toHaveTextContent(
      "Example collection unavailable",
    );
    await userEvent.click(canvas.getByRole("button", { name: "Retry" }));
    await expect(
      await canvas.findByText("This diagram set has no diagrams."),
    ).toBeVisible();
    await expect(args.onLoad).toHaveBeenLastCalledWith(target);
    await expect(canvas.queryByRole("alert")).not.toBeInTheDocument();
  },
};
export const Empty: Story = {
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText(
        "This diagram set has no diagrams.",
      ),
    ).toBeVisible();
  },
};
export const Populated: Story = {
  args: {
    onLoad: fn(async () =>
      fixtures.entity(
        empty.class,
        "Example diagrams",
        empty.properties,
        empty.links,
        [
          fixtures.embeddedEntity(
            ["diagram"],
            ["item"],
            "Example flow",
            {
              id: "example",
              kind: "flowchart",
              title: "Example flow",
              revision: 1,
              updated_at: "2026-10-15T08:30:00Z",
            },
            [fixtures.link("/example-flow", ["self"], "Example flow")],
          ),
        ],
        [],
      ),
    ),
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(
      await canvas.findByRole("link", { name: /Example flow/ }),
    );
    await expect(args.onFollow).toHaveBeenCalledWith(
      expect.objectContaining({ href: "/example-flow" }),
    );
  },
};
