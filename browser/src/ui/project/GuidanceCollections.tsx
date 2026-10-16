import {
  Anchor,
  Alert,
  Badge,
  Code,
  Group,
  Skeleton,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import type { Entity, SubEntity, Target } from "@siren-js/client";
import { useEffect, useState } from "react";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenContinuation } from "../siren/SirenContinuation";
import { ProjectActions } from "./ProjectActions";
import { ProjectPage, Section } from "./ProjectPrimitives";
import { projectPresentation } from "./ProjectPresentation";

type RecordResolution =
  | { kind: "loading" }
  | { kind: "resolved"; title: string }
  | { kind: "failed" };

type RecordReferenceProps = {
  item: SubEntity;
  onFollow: (target: Target) => void;
  onLoad: (target: Target) => Promise<Entity>;
  recordId: string;
};

function RecordReference({
  item,
  onFollow,
  onLoad,
  recordId,
}: RecordReferenceProps) {
  const [resolution, setResolution] = useState<RecordResolution>({
    kind: "loading",
  });
  const target = projectPresentation.recordTarget(item, recordId);

  useEffect(() => {
    let active = true;
    if (target.kind === "absent") {
      setResolution({ kind: "failed" });
      return () => {
        active = false;
      };
    }
    setResolution({ kind: "loading" });
    void onLoad(target.target).then(
      (record) => {
        if (active)
          setResolution({
            kind: "resolved",
            title: projectPresentation.title(record, "Guidance record"),
          });
      },
      () => {
        if (active) setResolution({ kind: "failed" });
      },
    );
    return () => {
      active = false;
    };
  }, [onLoad, recordId, target.kind === "present" ? target.target : recordId]);

  if (resolution.kind === "loading")
    return (
      <Skeleton
        aria-label={`Loading record ${recordId}`}
        height={32}
        role="status"
        width={220}
      />
    );
  if (resolution.kind === "failed" || target.kind === "absent")
    return (
      <Stack gap={2}>
        <Text c="dimmed" size="sm">
          Record title unavailable
        </Text>
        <Code>{recordId}</Code>
      </Stack>
    );
  return (
    <Stack gap={2}>
      <Anchor
        component="button"
        fw={600}
        onClick={() => onFollow(target.target)}
        type="button"
      >
        {resolution.title}
      </Anchor>
      <Code>{recordId}</Code>
    </Stack>
  );
}

export function GuidanceScopeCollection({
  entity,
  onFollow,
  onLoad,
  onRefresh,
}: SirenEntityProps) {
  const actionValues = {
    record_ids: entity.entities.map((item) =>
      projectPresentation.text(
        projectPresentation.itemProperties(item),
        "record_id",
      ),
    ),
  };
  return (
    <ProjectPage
      description="Ordered optional guidance eligible for routing to this project."
      title="Guidance scopes"
    >
      <ProjectActions
        actions={entity.actions}
        dangerNames={[]}
        omitNames={["find_guidance_scopes"]}
        onRefresh={onRefresh}
        primaryName="replace_guidance_scopes"
        values={actionValues}
      />
      <Section title="Eligible records">
        {entity.entities.length ? (
          <Table.ScrollContainer
            minWidth={620}
            scrollAreaProps={{
              viewportProps: {
                "aria-label": "Eligible guidance records",
                tabIndex: 0,
              },
            }}
          >
            <Table withTableBorder>
              <Table.Caption>Eligible guidance records</Table.Caption>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Position</Table.Th>
                  <Table.Th>Guidance record</Table.Th>
                  <Table.Th>Scope ID</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {entity.entities.map((item, index) => {
                  const properties = projectPresentation.itemProperties(item);
                  const id = projectPresentation.text(properties, "id");
                  const recordId = projectPresentation.text(
                    properties,
                    "record_id",
                  );
                  return (
                    <Table.Tr key={`${id}-${index}`}>
                      <Table.Td>
                        {projectPresentation.text(properties, "position")}
                      </Table.Td>
                      <Table.Td>
                        <RecordReference
                          item={item}
                          onFollow={onFollow}
                          onLoad={onLoad}
                          recordId={recordId}
                        />
                      </Table.Td>
                      <Table.Td>
                        <Code>{id}</Code>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        ) : (
          <Alert title="No optional guidance">
            This project does not advertise optional guidance scopes.
          </Alert>
        )}
        <SirenContinuation entity={entity} onFollow={onFollow} />
      </Section>
    </ProjectPage>
  );
}

export function GuidanceRelationshipCollection({
  entity,
  onFollow,
  onLoad,
  onRefresh,
}: SirenEntityProps) {
  const actionValues = {
    relationships: entity.entities.map((item) => {
      const properties = projectPresentation.itemProperties(item);
      return {
        kind: projectPresentation.text(properties, "kind"),
        source_record_id: projectPresentation.text(
          properties,
          "source_record_id",
        ),
        target_record_id: projectPresentation.text(
          properties,
          "target_record_id",
        ),
      };
    }),
  };
  return (
    <ProjectPage
      description="Typed relationships between authoritative guidance records."
      title="Guidance relationships"
    >
      <ProjectActions
        actions={entity.actions}
        dangerNames={[]}
        omitNames={["find_guidance_relationships"]}
        onRefresh={onRefresh}
        primaryName="replace_guidance_relationships"
        values={actionValues}
      />
      <Section title="Relationship graph">
        {entity.entities.length ? (
          <Stack>
            {entity.entities.map((item, index) => {
              const properties = projectPresentation.itemProperties(item);
              const id = projectPresentation.text(properties, "id");
              const source = projectPresentation.text(
                properties,
                "source_record_id",
              );
              const target = projectPresentation.text(
                properties,
                "target_record_id",
              );
              const kind = projectPresentation.text(properties, "kind");
              return (
                <Stack key={`${id}-${index}`} p="md" gap="sm">
                  <Group justify="space-between">
                    <Badge variant="light">
                      {projectPresentation.label(kind)}
                    </Badge>
                    <Code>{id}</Code>
                  </Group>
                  <Table variant="vertical">
                    <Table.Caption>Relationship endpoints</Table.Caption>
                    <Table.Tbody>
                      <Table.Tr>
                        <Table.Th>Source</Table.Th>
                        <Table.Td>
                          <RecordReference
                            item={item}
                            onFollow={onFollow}
                            onLoad={onLoad}
                            recordId={source}
                          />
                        </Table.Td>
                      </Table.Tr>
                      <Table.Tr>
                        <Table.Th>Target</Table.Th>
                        <Table.Td>
                          <RecordReference
                            item={item}
                            onFollow={onFollow}
                            onLoad={onLoad}
                            recordId={target}
                          />
                        </Table.Td>
                      </Table.Tr>
                    </Table.Tbody>
                  </Table>
                </Stack>
              );
            })}
          </Stack>
        ) : (
          <Alert title="No relationships">
            This project does not advertise guidance relationships.
          </Alert>
        )}
        <SirenContinuation entity={entity} onFollow={onFollow} />
      </Section>
    </ProjectPage>
  );
}
