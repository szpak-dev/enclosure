import { type Target } from "@siren-js/client";
import { sirenFixtures } from "../../stories/SirenFixtures";
import {
  OBJECT_CONTROL,
  STRUCTURED_FORM_EXTENSION,
} from "../siren/SirenActionForm";

export function targetHref(target: Target): string {
  return typeof target === "string" ? target : target.href.toString();
}

export const root = sirenFixtures.entity(
  ["api", "entry-point"],
  "Enclosure API",
  { title: "Enclosure API" },
  [],
  [],
  [],
);

export const projectItem = sirenFixtures.embeddedEntity(
  ["project"],
  ["item"],
  "Example service",
  { id: "project-1", title: "Example service" },
  [sirenFixtures.link("/siren/projects/project-1", ["item"], "Project")],
);
export const registerProject = sirenFixtures.action(
  "register_project",
  "Register a project",
  "/siren/projects",
  "POST",
  [],
);
export const projects = sirenFixtures.entity(
  ["collection", "project"],
  "Projects",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [projectItem],
  [registerProject],
);
export const emptyProjects = sirenFixtures.entity(
  ["collection", "project"],
  "Projects",
  { has_more: false, limit: 50, next_offset: 0 },
  [],
  [],
  [registerProject],
);

export const architectureItem = sirenFixtures.embeddedEntity(
  ["architecture-configuration"],
  ["item"],
  "Project architecture configuration",
  { id: "configuration-1", project_id: "project-1", revision: "revision-1" },
  [
    sirenFixtures.link(
      "/siren/projects/project-1/architecture-configurations/configuration-1",
      ["item"],
      "ProjectArchitectureConfiguration",
    ),
  ],
);
export const architectureCollection = sirenFixtures.entity(
  ["collection", "architecture-configuration"],
  "Architecture configurations",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [architectureItem],
  [],
);
export const architectureConfiguration = sirenFixtures.entity(
  ["architecture-configuration"],
  "Project architecture configuration",
  {
    boundaries_total_characters: 35,
    boundaries_yaml: "boundaries:\n  tags:\n    - name: app\n",
    id: "configuration-1",
    project_id: "project-1",
    revision: "revision-1",
    shape_total_characters: 43,
    shape_yaml: "shape:\n  realms:\n    - name: application\n",
  },
  [],
  [],
  [],
);
export const updateProject = sirenFixtures.action(
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
export const project = sirenFixtures.entity(
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

export const workspaceItem = sirenFixtures.embeddedEntity(
  ["workspace"],
  ["item"],
  "Workspace binding",
  {
    architecture_root: "/workspace",
    id: "workspace-1",
    project_id: "project-1",
    revision: 4,
    root: "/workspace",
  },
  [
    sirenFixtures.link(
      "/siren/projects/project-1/workspaces/workspace-1",
      ["item"],
      "WorkspaceBinding",
    ),
  ],
);
export const workspaces = sirenFixtures.entity(
  ["collection", "workspace"],
  "Workspaces",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [workspaceItem],
  [],
);
export const emptyWorkspaces = sirenFixtures.entity(
  ["collection", "workspace"],
  "Workspaces",
  { has_more: false, limit: 50, next_offset: 0 },
  [],
  [],
  [],
);
export const checkHealth = sirenFixtures.action(
  "check_project_health",
  "Check project health",
  "/siren/projects/project-1/workspaces/workspace-1/health-violations",
  "GET",
  [],
);
export const replaceWorkspace = sirenFixtures.action(
  "replace_workspace",
  "Replace a workspace binding",
  "/siren/projects/project-1/workspaces/workspace-1",
  "PUT",
  [
    sirenFixtures.field("root", "Root", "text"),
    sirenFixtures.field("architecture_root", "Architecture root", "text"),
    sirenFixtures.field("expected_revision", "Expected revision", "number"),
  ],
);
export const deleteWorkspace = sirenFixtures.action(
  "delete_workspace",
  "Delete a workspace binding",
  "/siren/projects/project-1/workspaces/workspace-1",
  "DELETE",
  [sirenFixtures.field("expected_revision", "Expected revision", "number")],
);
export const workspace = sirenFixtures.entity(
  ["workspace"],
  "Workspace binding",
  workspaceItem.properties,
  [],
  [],
  [checkHealth, replaceWorkspace, deleteWorkspace],
);
export const health = sirenFixtures.entity(
  ["command-result"],
  "Project health",
  {
    advisory_count: 1,
    failure_count: 0,
    healthy: true,
    revision: "health-revision-1",
  },
  [
    sirenFixtures.link(
      "/siren/projects/project-1/workspaces/workspace-1/health-attestation?expected_revision=health-revision-1",
      ["item"],
      "Architecture conformance attestation",
    ),
  ],
  [],
  [],
);

export const record = (id: string, title: string) =>
  sirenFixtures.entity(["record"], title, { id, title }, [], [], []);
export const scopeItem = sirenFixtures.embeddedEntity(
  ["guidance-scope"],
  ["item"],
  "Guidance scope",
  {
    id: "scope-1",
    position: 1,
    project_id: "project-1",
    record_id: "record-1",
  },
  [sirenFixtures.link("/siren/records/record-1", ["item"], "Record")],
);
export const guidanceScopes = sirenFixtures.entity(
  ["collection", "guidance-scope"],
  "Guidance scopes",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [scopeItem],
  [],
);
export const relationshipItem = sirenFixtures.embeddedEntity(
  ["guidance-relationship"],
  ["item"],
  "Guidance relationship",
  {
    id: "relationship-1",
    kind: "containment",
    project_id: "project-1",
    source_record_id: "record-1",
    target_record_id: "record-2",
  },
  [
    sirenFixtures.link("/siren/records/record-1", ["item"], "Record"),
    sirenFixtures.link("/siren/records/record-2", ["item"], "Record"),
  ],
);
export const guidanceRelationships = sirenFixtures.entity(
  ["collection", "guidance-relationship"],
  "Guidance relationships",
  { has_more: false, limit: 50, next_offset: 1 },
  [],
  [relationshipItem],
  [],
);

export const operatingContract = sirenFixtures.entity(
  ["operating-contract"],
  "Example operating contract",
  {
    authority: "example:contract",
    id: "contract-1",
    provenance: "storybook",
    title: "Example operating contract",
  },
  [],
  [],
  [],
);
