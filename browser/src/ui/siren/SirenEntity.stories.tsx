import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
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
};
