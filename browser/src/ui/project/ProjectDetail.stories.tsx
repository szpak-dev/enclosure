import type { Meta, StoryObj } from "@storybook/react-vite";
import type { Entity, Target } from "@siren-js/client";
import { expect, fn, userEvent, within } from "storybook/test";
import { sirenFixtures } from "../../stories/SirenFixtures";
import {
  OBJECT_CONTROL,
  STRUCTURED_FORM_EXTENSION,
} from "../siren/SirenActionForm";
import {
  SirenActionExecutionProvider,
  type SirenActionExecutor,
} from "../siren/SirenActionExecution";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { ProjectEntity } from "./ProjectEntity";

const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  { title: "Enclosure API" },
  [],
  [],
  [],
);
const configurationItem = sirenFixtures.embeddedEntity(
  ["architecture-configuration"],
  ["item"],
  "Project architecture configuration",
  { id: "configuration-1", revision: "revision-1" },
  [
    sirenFixtures.link(
      "/siren/projects/project-1/architecture-configurations/configuration-1",
      ["item"],
      "ProjectArchitectureConfiguration",
    ),
  ],
);
const configurationCollection = sirenFixtures.entity(
  ["collection", "architecture-configuration"],
  "Architecture configurations",
  { has_more: false, limit: 50 },
  [],
  [configurationItem],
  [],
);
const configuration = sirenFixtures.entity(
  ["architecture-configuration"],
  "Project architecture configuration",
  {
    boundaries_yaml: "boundaries:\n  tags: []\n",
    id: "configuration-1",
    shape_yaml: "shape:\n  realms: []\n",
  },
  [],
  [],
  [],
);
const updateProject = sirenFixtures.action(
  "update_project",
  "Update a project",
  "/siren/projects/project-1",
  "PUT",
  [
    sirenFixtures.field("title", "Title", "text"),
    sirenFixtures.field("boundaries_yaml", "Boundaries YAML", "text"),
    sirenFixtures.field("shape_yaml", "Shape YAML", "text"),
    sirenFixtures.field("scaffolding_id", "Scaffolding ID", "text"),
  ],
);
Object.assign(updateProject, {
  [STRUCTURED_FORM_EXTENSION]: {
    controls: [
      {
        control: OBJECT_CONTROL,
        location: "body",
        mediaType: "application/json",
        name: "stack",
        required: true,
        schema: {
          additionalProperties: false,
          properties: {
            language: { title: "Language", type: "string" },
            language_version: { title: "Language version", type: "string" },
            package_manager: { title: "Package manager", type: "string" },
          },
          required: ["language", "language_version", "package_manager"],
          title: "Detected stack",
          type: "object",
        },
      },
    ],
    version: "1",
  },
});
const project = sirenFixtures.entity(
  ["project"],
  "Example service",
  {
    id: "project-1",
    language_id: "python",
    language_version: "",
    package_manager_id: "uv",
    scaffolding_id: "scaffolding-1",
    title: "Example service",
  },
  [
    sirenFixtures.link(
      "/siren/projects/project-1/workspaces",
      ["collection"],
      "WorkspaceBinding",
    ),
    sirenFixtures.link(
      "/siren/projects/project-1/architecture-configurations",
      ["collection"],
      "ProjectArchitectureConfiguration",
    ),
    sirenFixtures.link(
      "/siren/projects/project-1/guidance-scopes",
      ["collection"],
      "GuidanceScope",
    ),
  ],
  [],
  [updateProject],
);

function href(target: Target): string {
  return typeof target === "string" ? target : target.href.toString();
}

const meta = {
  component: ProjectEntity,
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async () => ({ kind: "empty" }));
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  args: {
    entity: project,
    onFollow: fn(),
    onLoad: fn(async (target: Target): Promise<Entity> =>
      href(target).endsWith("architecture-configurations")
        ? configurationCollection
        : configuration,
    ),
    onRefresh: fn(),
    onSubmit: fn(),
    root,
  },
  title: "Browser/Projects/Project detail",
} satisfies Meta<SirenEntityProps>;

export default meta;
type Story = StoryObj<SirenEntityProps>;

export const Configured: Story = {
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("heading", { level: 1, name: "Example service" }),
    ).toBeVisible();
    await expect(canvas.getByText("Not reported")).toBeVisible();
    const update = await canvas.findByRole("button", {
      name: "Update a project",
    });
    await expect(update).toBeVisible();
    await canvas.getByRole("link", { name: /Workspaces/ }).click();
    await expect(args.onFollow).toHaveBeenCalledWith(
      expect.objectContaining({ href: "/siren/projects/project-1/workspaces" }),
    );
    await userEvent.click(update);
    const dialog = await within(canvasElement.ownerDocument.body).findByRole(
      "dialog",
      { name: "Update a project" },
    );
    await expect(
      within(dialog).getByRole("textbox", { name: "Language" }),
    ).toHaveValue("python");
    await expect(
      within(dialog).getByRole("textbox", { name: "Language version" }),
    ).toHaveValue("");
    await expect(
      within(dialog).getByRole("textbox", { name: "Package manager" }),
    ).toHaveValue("uv");
    await expect(
      within(dialog).getByRole("textbox", { name: "Boundaries YAML" }),
    ).toHaveValue("boundaries:\n  tags: []\n");
  },
};

export const ConfigurationUnavailable: Story = {
  args: {
    onLoad: fn(async (): Promise<Entity> => {
      throw new Error("Configuration unavailable");
    }),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("alert")).toHaveTextContent(
      "update form is withheld",
    );
    await expect(
      canvas.queryByRole("button", { name: "Update a project" }),
    ).not.toBeInTheDocument();
    await expect(
      canvas.getByRole("link", { name: /Workspaces/ }),
    ).toBeVisible();
  },
};
