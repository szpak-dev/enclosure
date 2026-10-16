import { Paper } from "@mantine/core";
import { ResourcePage, Section } from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { ProjectActionResult } from "./ProjectActionResult";
import { ProjectActions } from "./ProjectActions";

export function ProjectArtifactEntity({ entity, onRefresh }: SirenEntityProps) {
  const ignored = entity.actions
    .filter(
      (action) =>
        action.method === "GET" &&
        entity.links.some(
          (link) =>
            link.rel.includes("self") &&
            link.href.toString() === action.href.toString(),
        ),
    )
    .map((action) => action.name);
  let primaryName = "";
  entity.actions.forEach((action) => {
    if (ignored.includes(action.name)) return;
    if (!primaryName || action.method !== "GET") primaryName = action.name;
  });
  return (
    <ResourcePage
      description="Revision-pinned Projects evidence and its advertised operations."
      title={entity.title || "Project evidence"}
    >
      <ProjectActions
        actions={entity.actions}
        dangerNames={[]}
        omitNames={ignored}
        onRefresh={onRefresh}
        primaryName={primaryName}
        values={entity.properties}
      />
      <Section title="Evidence">
        <Paper p="md" radius="md" withBorder>
          <ProjectActionResult actionName="artifact" entity={entity} />
        </Paper>
      </Section>
    </ResourcePage>
  );
}
