import {
  Alert,
  Badge,
  Button,
  Code,
  Group,
  Paper,
  Skeleton,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import type { Action, Entity, Target } from "@siren-js/client";
import { useEffect, useState } from "react";
import { SirenResponseError } from "../../client/SirenClient";
import {
  ResourceActions,
  type ResourceActionScope,
} from "../resource/ResourceActions";
import {
  Identity,
  ResourcePage,
  Section,
} from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import {
  ScaffoldingActionResult,
  type ScaffoldingRenderingActions,
} from "./ScaffoldingActionResult";
import {
  scaffoldingPresentation,
  type ScaffoldingSpec,
} from "./ScaffoldingPresentation";
import {
  ScaffoldingTemplateHydrator,
  type TemplateInput,
} from "./ScaffoldingTemplateHydrator";

type UpdateValues =
  | { kind: "loading" }
  | { kind: "unavailable"; message: string }
  | { kind: "ready"; values: object };

function hydratedUpdateValues(
  entity: Entity,
  spec: ScaffoldingSpec,
  templates: readonly TemplateInput[],
): object {
  return {
    description: scaffoldingPresentation.string(
      entity.properties,
      "description",
    ),
    language_id: scaffoldingPresentation.string(
      entity.properties,
      "language_id",
    ),
    name: scaffoldingPresentation.string(entity.properties, "name"),
    spec: {
      language: spec.language,
      templates,
      variables: spec.variables.map((variable) => ({
        name: variable.name,
        type: variable.type,
      })),
    },
  };
}

function typedActions(
  actions: readonly Action[],
  spec: ScaffoldingSpec,
  updateValues: UpdateValues,
): Action[] {
  return actions
    .filter(
      (action) =>
        updateValues.kind === "ready" || action.name !== "update_scaffolding",
    )
    .map((action) =>
      action.name === "render_scaffolding" ||
      action.name === "read_scaffolding_rendered_file"
        ? scaffoldingPresentation.typedRenderingAction(action, spec.variables)
        : action,
    );
}

function collectionTarget(root: Entity): Target | undefined {
  return root.links.find(
    (link) =>
      link.rel.includes("collection") &&
      link.href.toString().endsWith("/scaffoldings"),
  );
}

type ScaffoldingActionsProps = {
  actions: readonly Action[];
  onFollow: (target: Target) => void;
  onRefresh: () => void;
  renderingActions: ScaffoldingRenderingActions;
  root: Entity;
  scope: ResourceActionScope;
  values: object;
};

function ScaffoldingActions({
  actions,
  onFollow,
  onRefresh,
  renderingActions,
  root,
  scope,
  values,
}: ScaffoldingActionsProps) {
  return (
    <ResourceActions
      actions={actions}
      dangerDescription="Deleting this scaffolding permanently removes its metadata, variables, and complete template specification."
      dangerNames={["delete_scaffolding"]}
      omitNames={[
        "get_scaffolding",
        "read_scaffolding_rendered_file",
        "read_scaffolding_template",
      ]}
      onCompleted={(action) => {
        if (action.name === "update_scaffolding") onRefresh();
        if (action.name === "delete_scaffolding") {
          const target = collectionTarget(root);
          if (target) onFollow(target);
        }
      }}
      primaryName="render_scaffolding"
      renderResult={({ actionName, entity: result, values: resultValues }) => (
        <ScaffoldingActionResult
          actionName={actionName}
          entity={result}
          onFollow={onFollow}
          renderingActions={renderingActions}
          values={resultValues}
        />
      )}
      resolveError={(action, reason) => {
        if (
          action.name === "delete_scaffolding" &&
          reason instanceof SirenResponseError &&
          reason.status === 409 &&
          reason.entity &&
          scaffoldingPresentation.string(
            reason.entity.properties,
            "reason_code",
          ) === "destructive_approval_required"
        )
          return {
            kind: "conflict",
            conflict: {
              description:
                "Deletion has not run. Approve the exact one-time request shown below through an authorized security client, then submit Delete a scaffolding again before it expires.",
              entity: reason.entity,
              title: "One-time approval required",
            },
          };
        return { kind: "unhandled" };
      }}
      scope={scope}
      values={values}
    />
  );
}

export function ScaffoldingEntity({
  entity,
  onFollow,
  onLoad,
  onRefresh,
  root,
}: SirenEntityProps) {
  const specState = scaffoldingPresentation.spec(entity.properties);
  const manifests = scaffoldingPresentation.manifestTarget(entity);
  const [updateValues, setUpdateValues] = useState<UpdateValues>({
    kind: "loading",
  });

  useEffect(() => {
    let active = true;
    if (specState.kind === "unavailable" || manifests.kind === "absent") {
      setUpdateValues({
        kind: "unavailable",
        message:
          "The specification or its revision-pinned template manifest is unavailable.",
      });
      return () => {
        active = false;
      };
    }
    setUpdateValues({ kind: "loading" });
    const hydrator = new ScaffoldingTemplateHydrator(onLoad);
    void hydrator.hydrate(manifests.target).then(
      (templates) => {
        if (active)
          setUpdateValues({
            kind: "ready",
            values: hydratedUpdateValues(entity, specState.spec, templates),
          });
      },
      (reason: unknown) => {
        if (active)
          setUpdateValues({
            kind: "unavailable",
            message:
              reason instanceof Error
                ? reason.message
                : "Unable to load revision-pinned templates.",
          });
      },
    );
    return () => {
      active = false;
    };
  }, [
    entity,
    manifests.kind === "present" ? manifests.target : entity,
    onLoad,
    specState.kind,
  ]);

  if (specState.kind === "unavailable")
    return (
      <ResourcePage
        description="The scaffolding contract could not be presented safely."
        title="Scaffolding unavailable"
      >
        <Alert color="red" role="alert" title="Malformed scaffolding">
          The server response does not contain a complete scaffolding
          specification.
        </Alert>
      </ResourcePage>
    );

  const actions = typedActions(entity.actions, specState.spec, updateValues);
  const renderAction = actions.find(
    (action) => action.name === "render_scaffolding",
  );
  const readAction = actions.find(
    (action) => action.name === "read_scaffolding_rendered_file",
  );
  const renderingActions =
    renderAction && readAction
      ? { kind: "available" as const, read: readAction, render: renderAction }
      : { kind: "unavailable" as const };
  const title = scaffoldingPresentation.text(entity.properties, "name");
  const id = scaffoldingPresentation.text(entity.properties, "id");

  return (
    <ResourcePage
      description={scaffoldingPresentation.text(
        entity.properties,
        "description",
      )}
      title={title}
    >
      <Group justify="space-between">
        <Identity label="Scaffolding ID" value={id} />
        <Badge size="lg" variant="light">
          {scaffoldingPresentation.text(entity.properties, "language_id")}
        </Badge>
      </Group>
      <ScaffoldingActions
        actions={actions}
        onFollow={onFollow}
        onRefresh={onRefresh}
        renderingActions={renderingActions}
        root={root}
        scope="safe"
        values={updateValues.kind === "ready" ? updateValues.values : {}}
      />
      {updateValues.kind === "loading" ? (
        <Skeleton
          aria-label="Loading complete template specification"
          height={36}
          role="status"
          width={320}
        />
      ) : null}
      {updateValues.kind === "unavailable" ? (
        <Alert color="orange" title="Update unavailable" variant="outline">
          {updateValues.message} Rendering and revision-pinned inspection remain
          available, but the update form is withheld to protect template
          content.
        </Alert>
      ) : null}
      <Section title="Rendering variables">
        {specState.spec.variables.length ? (
          <Table.ScrollContainer
            minWidth={520}
            scrollAreaProps={{
              viewportProps: {
                "aria-label": "Rendering variables",
                tabIndex: 0,
              },
            }}
          >
            <Table withTableBorder>
              <Table.Caption>Declared rendering variables</Table.Caption>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Name</Table.Th>
                  <Table.Th>Required type</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {specState.spec.variables.map((variable) => (
                  <Table.Tr key={variable.name}>
                    <Table.Td>
                      <Code>{variable.name}</Code>
                    </Table.Td>
                    <Table.Td>{variable.type}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        ) : (
          <Alert title="No rendering variables">
            This scaffolding renders without parameters.
          </Alert>
        )}
      </Section>
      <Section title="Templates">
        <Paper p="lg" radius="md" withBorder>
          <Stack>
            <Group justify="space-between">
              <Stack gap={2}>
                <Text fw={600}>
                  {scaffoldingPresentation.text(
                    entity.properties,
                    "template_count",
                  )}{" "}
                  templates
                </Text>
                <Text c="dimmed" size="sm">
                  Revision-pinned manifests keep large template bodies out of
                  the detail response.
                </Text>
              </Stack>
              {manifests.kind === "present" ? (
                <Button
                  component="a"
                  href={`#${typeof manifests.target === "string" ? manifests.target : manifests.target.href}`}
                  onClick={(event) => {
                    event.preventDefault();
                    onFollow(manifests.target);
                  }}
                  variant="light"
                >
                  Browse templates
                </Button>
              ) : (
                <Text c="dimmed">Manifest navigation unavailable.</Text>
              )}
            </Group>
            <Identity
              label="Template-set revision"
              value={scaffoldingPresentation.text(
                entity.properties,
                "templates_revision",
              )}
            />
          </Stack>
        </Paper>
      </Section>
      <ScaffoldingActions
        actions={actions}
        onFollow={onFollow}
        onRefresh={onRefresh}
        renderingActions={renderingActions}
        root={root}
        scope="danger"
        values={updateValues.kind === "ready" ? updateValues.values : {}}
      />
    </ResourcePage>
  );
}
