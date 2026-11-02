import { Entity, type Target } from "@siren-js/client";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import { SirenResponseError } from "../../client/SirenClient";
import { sirenFixtures } from "../../stories/SirenFixtures";
import {
  SirenActionExecutionProvider,
  type SirenActionExecutor,
} from "../siren/SirenActionExecution";
import type { SirenEntityProps } from "../siren/SirenEntity";
import {
  ArchitectureConfigurationCollection,
  ArchitectureConfigurationEntity,
} from "./ArchitectureConfiguration";
import {
  GuidanceRelationshipCollection,
  GuidanceScopeCollection,
} from "./GuidanceCollections";
import { ProjectArtifactEntity } from "./ProjectArtifactEntity";
import { ProjectCollection } from "./ProjectCollection";
import { ProjectEntity } from "./ProjectEntity";
import { WorkspaceCollection } from "./WorkspaceCollection";
import { WorkspaceEntity } from "./WorkspaceEntity";

import {
  architectureCollection,
  architectureConfiguration,
  emptyProjects,
  emptyWorkspaces,
  guidanceRelationships,
  guidanceScopes,
  health,
  operatingContract,
  project,
  projects,
  record,
  root,
  targetHref,
  workspace,
  workspaces,
} from "./ProjectStoryFixtures";

const meta = {
  component: ProjectCollection,
  args: {
    entity: projects,
    onFollow: fn(),
    onLoad: fn(async () => architectureConfiguration),
    onRefresh: fn(),
    onSubmit: fn(),
    root,
  },
  title: "Browser/Projects/Project collection",
} satisfies Meta<SirenEntityProps>;

export default meta;
type Story = StoryObj<SirenEntityProps>;

export const PopulatedProjects: Story = {
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    const row = canvas.getByRole("listitem");
    const open = canvas.getByRole("link", { name: "Open project" });
    const bounds = row.getBoundingClientRect();
    await expect(
      bounds.right - open.getBoundingClientRect().right,
    ).toBeGreaterThanOrEqual(15);
    await expect(
      bounds.right - open.getBoundingClientRect().right,
    ).toBeLessThanOrEqual(17);
    await expect(open.getBoundingClientRect().left).toBeGreaterThan(
      bounds.left + bounds.width / 2,
    );

    await userEvent.click(canvas.getByRole("link", { name: "Open project" }));
    await expect(args.onFollow).toHaveBeenCalledWith(
      expect.objectContaining({ href: "/siren/projects/project-1" }),
    );
  },
};

export const EmptyProjects: Story = {
  args: { entity: emptyProjects },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent(
      "No projects yet",
    );
  },
};

export const NarrowProjects: Story = {
  parameters: { viewport: { defaultViewport: "mobile1" } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("heading", { name: "Projects" }),
    ).toBeVisible();
    await expect(
      canvas.getByRole("button", { name: "Register a project" }),
    ).toBeVisible();
    await expect(
      canvas.getByRole("link", { name: "Open project" }),
    ).toBeVisible();
  },
};

export const ProjectRegistrationSuccess: Story = {
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async () => ({
        entity: project,
        kind: "entity",
      }));
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Register a project" }),
    );
    const dialog = await page.findByRole("dialog", {
      name: "Register a project",
    });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Register a project" }),
    );
    await expect(await within(dialog).findByRole("status")).toHaveTextContent(
      "Action completed",
    );
  },
};

export const ProjectRegistrationFailure: Story = {
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async () => {
        throw new SirenResponseError(
          422,
          "/siren/projects",
          "Architecture root is required.",
        );
      });
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Register a project" }),
    );
    const dialog = await page.findByRole("dialog", {
      name: "Register a project",
    });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Register a project" }),
    );
    await expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Architecture root is required.",
    );
  },
};

export const ProjectDetail: Story = {
  args: {
    entity: project,
    onLoad: fn(async (target: Target) =>
      targetHref(target).endsWith("architecture-configurations")
        ? architectureCollection
        : architectureConfiguration,
    ),
  },
  render: (args) => <ProjectEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Not reported")).toBeVisible();
    await expect(
      await canvas.findByRole("button", { name: "Update a project" }),
    ).toBeVisible();
    await expect(
      canvas.getByRole("link", { name: /Workspaces/ }),
    ).toBeVisible();
  },
};

export const PopulatedWorkspaces: Story = {
  args: { entity: workspaces },
  render: (args) => <WorkspaceCollection {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getAllByText("/workspace")[0]).toBeVisible();
    await expect(canvas.getByRole("link", { name: "Open" })).toBeVisible();
  },
};

export const EmptyWorkspaces: Story = {
  args: { entity: emptyWorkspaces },
  render: (args) => <WorkspaceCollection {...args} />,
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent(
      "No workspaces bound",
    );
  },
};

export const WorkspaceHealthSuccess: Story = {
  args: { entity: workspace },
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async () => ({
        entity: health,
        kind: "entity",
      }));
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  render: (args) => <WorkspaceEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Check project health" }),
    );
    const dialog = await page.findByRole("dialog", {
      name: "Check project health",
    });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Check project health" }),
    );
    await expect(await within(dialog).findByRole("status")).toHaveTextContent(
      "Action completed",
    );
    await expect(within(dialog).getByText("health-revision-1")).toBeVisible();
  },
};

export const WorkspaceConflict: Story = {
  args: { entity: workspace },
  decorators: [
    (Story) => {
      const execute = fn<SirenActionExecutor>(async () => {
        throw new SirenResponseError(
          409,
          "/siren/projects/project-1/workspaces/workspace-1",
          "The workspace changed before submission.",
        );
      });
      return (
        <SirenActionExecutionProvider execute={execute}>
          <Story />
        </SirenActionExecutionProvider>
      );
    },
  ],
  render: (args) => <WorkspaceEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(canvas.getByRole("button", { name: "More actions" }));
    await userEvent.click(
      await page.findByRole("menuitem", {
        name: "Replace a workspace binding",
      }),
    );
    const dialog = await page.findByRole("dialog", {
      name: "Replace a workspace binding",
    });
    await userEvent.click(
      within(dialog).getByRole("button", {
        name: "Replace a workspace binding",
      }),
    );
    await expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "The workspace changed before submission.",
    );
  },
};

export const WorkspaceDeleteConfirmation: Story = {
  args: { entity: workspace },
  render: (args) => <WorkspaceEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const page = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      canvas.getByRole("button", { name: "Delete a workspace binding" }),
    );
    const confirmation = await page.findByRole("dialog", {
      name: "Delete a workspace binding?",
    });
    await expect(
      within(confirmation).getByText(/remove project configuration/),
    ).toBeVisible();
    await userEvent.click(
      within(confirmation).getByRole("button", { name: "Cancel" }),
    );
    await waitFor(() =>
      expect(
        page.queryByRole("dialog", { name: "Delete a workspace binding?" }),
      ).not.toBeInTheDocument(),
    );
  },
};

export const ArchitectureCollectionEmpty: Story = {
  args: {
    entity: sirenFixtures.entity(
      ["collection", "architecture-configuration"],
      "Architecture configurations",
      { has_more: false, limit: 50, next_offset: 0 },
      [],
      [],
      [],
    ),
  },
  render: (args) => <ArchitectureConfigurationCollection {...args} />,
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent(
      "No architecture configuration",
    );
  },
};

export const ArchitectureDocuments: Story = {
  args: { entity: architectureConfiguration },
  render: (args) => <ArchitectureConfigurationEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByLabelText("boundaries YAML configuration"),
    ).toBeVisible();
    await userEvent.click(canvas.getByRole("tab", { name: "Shape" }));
    await expect(
      canvas.getByLabelText("shape YAML configuration"),
    ).toBeVisible();
  },
};

export const GuidanceResolved: Story = {
  args: {
    entity: guidanceScopes,
    onLoad: fn(async () => record("record-1", "Delivery guidance")),
  },
  render: (args) => <GuidanceScopeCollection {...args} />,
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByRole("button", {
        name: "Delivery guidance",
      }),
    ).toBeVisible();
  },
};

export const GuidanceLoading: Story = {
  args: {
    entity: guidanceScopes,
    onLoad: fn(() => new Promise<Entity>(() => {})),
  },
  render: (args) => <GuidanceScopeCollection {...args} />,
  play: async ({ canvasElement }) => {
    await expect(
      within(canvasElement).getByLabelText("Loading record record-1"),
    ).toBeVisible();
  },
};

export const GuidanceFailure: Story = {
  args: {
    entity: guidanceScopes,
    onLoad: fn(async () => {
      throw new Error("Record unavailable");
    }),
  },
  render: (args) => <GuidanceScopeCollection {...args} />,
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Record title unavailable"),
    ).toBeVisible();
  },
};

export const GuidanceRelationships: Story = {
  args: {
    entity: guidanceRelationships,
    onLoad: fn(async (target: Target) =>
      targetHref(target).endsWith("record-1")
        ? record("record-1", "Delivery lifecycle")
        : record("record-2", "Verification policy"),
    ),
  },
  render: (args) => <GuidanceRelationshipCollection {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Containment")).toBeVisible();
    await expect(
      await canvas.findByRole("button", { name: "Delivery lifecycle" }),
    ).toBeVisible();
    await expect(
      await canvas.findByRole("button", { name: "Verification policy" }),
    ).toBeVisible();
  },
};

export const OperatingContractEvidence: Story = {
  args: { entity: operatingContract },
  render: (args) => <ProjectArtifactEntity {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("example:contract")).toBeVisible();
    await expect(canvas.getByText("storybook")).toBeVisible();
  },
};
