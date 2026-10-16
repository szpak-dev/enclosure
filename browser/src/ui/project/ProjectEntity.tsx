import { Alert, Paper, Skeleton, Stack } from "@mantine/core";
import type { Link } from "@siren-js/client";
import { useEffect, useState } from "react";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { ProjectActions } from "./ProjectActions";
import {
  Identity,
  ProjectPage,
  PropertyTable,
  ResourceCards,
  Section,
} from "./ProjectPrimitives";
import { projectPresentation } from "./ProjectPresentation";

export function ProjectEntity({
  entity,
  onFollow,
  onLoad,
  onRefresh,
}: SirenEntityProps) {
  const links = entity.links.filter((link) => !link.rel.includes("self"));
  const runtime: Link[] = [];
  const governance: Link[] = [];
  links.forEach((link) => {
    if (link.title === "WorkspaceBinding") runtime.push(link);
    else governance.push(link);
  });
  const title = projectPresentation.title(entity, "Project");
  const id = projectPresentation.text(entity.properties, "id");
  const configurationLink = governance.find(
    (link) => link.title === "ProjectArchitectureConfiguration",
  );
  type UpdateValues =
    | { kind: "loading" }
    | { kind: "unavailable" }
    | { kind: "ready"; values: object };
  const [updateValues, setUpdateValues] = useState<UpdateValues>(
    configurationLink ? { kind: "loading" } : { kind: "unavailable" },
  );

  useEffect(() => {
    let active = true;
    if (!configurationLink) {
      setUpdateValues({ kind: "unavailable" });
      return () => {
        active = false;
      };
    }
    setUpdateValues({ kind: "loading" });
    void onLoad(configurationLink).then(
      async (collection) => {
        const item = collection.entities[0];
        if (!item) {
          if (active) setUpdateValues({ kind: "unavailable" });
          return;
        }
        const target = projectPresentation.itemTarget(item);
        if (target.kind === "absent") {
          if (active) setUpdateValues({ kind: "unavailable" });
          return;
        }
        const configuration = await onLoad(target.target);
        if (active)
          setUpdateValues({
            kind: "ready",
            values: Object.assign({}, entity.properties, {
              boundaries_yaml: projectPresentation.text(
                configuration.properties,
                "boundaries_yaml",
              ),
              shape_yaml: projectPresentation.text(
                configuration.properties,
                "shape_yaml",
              ),
              stack: {
                language: projectPresentation.inputText(
                  entity.properties,
                  "language_id",
                ),
                language_version: projectPresentation.inputText(
                  entity.properties,
                  "language_version",
                ),
                package_manager: projectPresentation.inputText(
                  entity.properties,
                  "package_manager_id",
                ),
              },
            }),
          });
      },
      () => {
        if (active) setUpdateValues({ kind: "unavailable" });
      },
    );
    return () => {
      active = false;
    };
  }, [configurationLink, entity.properties, onLoad]);

  const actions =
    updateValues.kind === "ready"
      ? entity.actions
      : entity.actions.filter((action) => action.name !== "update_project");

  return (
    <ProjectPage
      description="Identity, runtime bindings, architecture, and governing guidance."
      title={title}
    >
      <Identity label="Project ID" value={id} />
      <ProjectActions
        actions={actions}
        dangerNames={[]}
        omitNames={["get_project"]}
        onRefresh={onRefresh}
        primaryName="update_project"
        values={
          updateValues.kind === "ready"
            ? updateValues.values
            : entity.properties
        }
      />
      {updateValues.kind === "loading" ? (
        <Skeleton
          aria-label="Loading project configuration"
          height={36}
          role="status"
          width={280}
        />
      ) : null}
      {updateValues.kind === "unavailable" ? (
        <Alert color="dark" title="Update unavailable" variant="outline">
          The advertised architecture configuration could not be loaded, so the
          update form is withheld to protect the existing configuration.
        </Alert>
      ) : null}
      <Section title="Project metadata">
        <Paper p="md" radius="md" withBorder>
          <PropertyTable
            caption="Project metadata"
            properties={entity.properties}
            visible={[
              "language_id",
              "language_version",
              "package_manager_id",
              "scaffolding_id",
            ]}
          />
        </Paper>
      </Section>
      <Stack gap="xl">
        <Section title="Runtime">
          <ResourceCards links={runtime} onFollow={onFollow} />
        </Section>
        <Section title="Governance">
          <ResourceCards links={governance} onFollow={onFollow} />
        </Section>
      </Stack>
    </ProjectPage>
  );
}
