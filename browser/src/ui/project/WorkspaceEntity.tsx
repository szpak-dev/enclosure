import { Paper } from "@mantine/core";
import {
  Identity,
  PropertyTable,
  ResourcePage,
  Section,
} from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { ProjectActions } from "./ProjectActions";
import { projectPresentation } from "./ProjectPresentation";

export function WorkspaceEntity({ entity, onRefresh }: SirenEntityProps) {
  const root = projectPresentation.text(entity.properties, "root");
  const id = projectPresentation.text(entity.properties, "id");
  return (
    <ResourcePage
      description="Local availability, generation tools, health evidence, and insights."
      title={root}
    >
      <Identity label="Workspace ID" value={id} />
      <ProjectActions
        actions={entity.actions}
        dangerNames={["delete_workspace"]}
        omitNames={["get_workspace"]}
        onRefresh={onRefresh}
        primaryName="check_project_health"
        values={entity.properties}
      />
      <Section title="Workspace binding">
        <Paper p="md" radius="md" withBorder>
          <PropertyTable
            caption="Workspace binding details"
            label={(name) => projectPresentation.label(name)}
            properties={entity.properties}
            text={(properties, name) =>
              projectPresentation.text(properties, name)
            }
            visible={["root", "architecture_root", "project_id", "revision"]}
          />
        </Paper>
      </Section>
    </ResourcePage>
  );
}
