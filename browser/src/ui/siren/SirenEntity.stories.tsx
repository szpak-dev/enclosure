import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";
import { OBJECT_CONTROL, STRUCTURED_FORM_EXTENSION } from "./SirenActionForm";
import { SirenEntity } from "./SirenEntity";

const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  { title: "Enclosure API" },
  [],
  [],
  [],
);

const meta = {
  component: SirenEntity,
  args: {
    onFollow: fn(),
    onLoad: fn(),
    onRefresh: fn(),
    onSubmit: fn(),
    root,
  },
  title: "Browser/Siren/Entity",
} satisfies Meta<typeof SirenEntity>;

export default meta;
type Story = StoryObj<typeof meta>;

export const GenericEntity: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["workspace"],
      "Local workspace",
      { root: "/workspace", status: "ready" },
      [
        sirenFixtures.link("/siren/projects/project-1", ["project"], "Project"),
        sirenFixtures.link("/siren/records/record-1", ["guidance"], "Guidance"),
      ],
      [],
      [],
    ),
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("heading", { name: "Local workspace" }),
    ).toBeVisible();
    await userEvent.click(canvas.getByRole("link", { name: "Project" }));
    await expect(args.onFollow).toHaveBeenCalledWith(
      "/siren/projects/project-1",
    );
  },
};

export const ActionForm: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["project"],
      "Enclosure",
      { title: "Enclosure" },
      [],
      [],
      [
        sirenFixtures.action(
          "rename-project",
          "Rename project",
          "/siren/projects/project-1",
          "PATCH",
          [sirenFixtures.field("title", "Project title", "text")],
        ),
      ],
    ),
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    const title = canvas.getByRole("textbox", { name: "Project title" });
    await userEvent.clear(title);
    await userEvent.type(title, "Updated project");
    await userEvent.click(
      canvas.getByRole("button", { name: "Rename project" }),
    );
    await expect(args.onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ name: "rename-project" }),
      { title: "Updated project" },
    );
  },
};

const structuredAction = sirenFixtures.action(
  "apply-command",
  "Apply command",
  "/siren/diagrams/diagram-1/commands",
  "POST",
  [],
);
Object.assign(structuredAction, {
  [STRUCTURED_FORM_EXTENSION]: {
    controls: [
      {
        control: OBJECT_CONTROL,
        location: "body",
        mediaType: "application/json",
        name: "arguments",
        required: true,
        schema: {
          additionalProperties: false,
          properties: {
            element_id: { minLength: 1, title: "Element id", type: "string" },
          },
          required: ["element_id"],
          title: "Command arguments",
          type: "object",
        },
      },
    ],
    version: "1",
  },
});

export const StructuredValidationFailure: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["diagram"],
      "Command validation",
      { title: "Command validation" },
      [],
      [],
      [structuredAction],
    ),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Submit the empty command to display the structured validation failure.",
      },
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(
      canvas.getByRole("button", { name: "Apply command" }),
    );
    await expect(await canvas.findByRole("alert")).toBeVisible();
  },
};

export const FieldlessAction: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["status"],
      "Runtime status",
      { status: "ready" },
      [],
      [],
      [
        sirenFixtures.action(
          "refresh-status",
          "Refresh status",
          "/siren/status",
          "GET",
          [],
        ),
      ],
    ),
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(
      canvas.getByRole("button", { name: "Refresh status" }),
    );
    await expect(args.onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ name: "refresh-status" }),
      {},
    );
  },
};

export const SubmissionFailure: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["project"],
      "Conflicting project",
      { title: "Conflicting project" },
      [],
      [],
      [
        sirenFixtures.action(
          "rename-project",
          "Rename project",
          "/siren/projects/project-1",
          "PATCH",
          [sirenFixtures.field("title", "Project title", "text")],
        ),
      ],
    ),
    onSubmit: fn(async () => {
      throw new Error("The project changed before submission.");
    }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(
      canvas.getByRole("button", { name: "Rename project" }),
    );
    await expect(await canvas.findByRole("alert")).toHaveTextContent(
      "The project changed before submission.",
    );
  },
};
