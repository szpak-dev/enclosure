import {
  Alert,
  Badge,
  Button,
  Code,
  Group,
  Loader,
  Paper,
  ScrollArea,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import type { Entity, Target } from "@siren-js/client";
import { useEffect, useState } from "react";
import {
  Identity,
  ResourcePage,
  Section,
} from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenContinuation } from "../siren/SirenContinuation";
import { scaffoldingPresentation } from "./ScaffoldingPresentation";

type TemplateSelection =
  | { kind: "none" }
  | { kind: "loading" }
  | { kind: "failed"; message: string }
  | { kind: "ready"; entity: Entity };

type TemplateContentProps = {
  entity: Entity;
  onLoad: (target: Target) => Promise<Entity>;
};

function TemplateContent({ entity, onLoad }: TemplateContentProps) {
  const initialContent = scaffoldingPresentation.string(
    entity.properties,
    "content",
  );
  const [page, setPage] = useState(entity);
  const [content, setContent] = useState(() => initialContent ?? "");
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState(() =>
    initialContent === undefined
      ? "The template response contains malformed content."
      : "",
  );
  const next = page.links.find((link) => link.rel.includes("next"));

  useEffect(() => {
    const nextContent = scaffoldingPresentation.string(
      entity.properties,
      "content",
    );
    setPage(entity);
    setContent(nextContent ?? "");
    setFailure(
      nextContent === undefined
        ? "The template response contains malformed content."
        : "",
    );
  }, [entity]);

  return (
    <Paper p="lg" radius="md" withBorder>
      <Stack>
        <Group justify="space-between">
          <Stack gap={2}>
            <Title order={3} size="h4">
              {scaffoldingPresentation.text(page.properties, "path")}
            </Title>
            <Text c="dimmed" size="sm">
              {scaffoldingPresentation.text(page.properties, "write_mode")}
            </Text>
          </Stack>
          <Badge variant="outline">
            {scaffoldingPresentation.text(page.properties, "total_characters")}{" "}
            characters
          </Badge>
        </Group>
        <Identity
          label="Template revision"
          value={scaffoldingPresentation.text(page.properties, "revision")}
        />
        <ScrollArea.Autosize
          mah="32rem"
          type="auto"
          viewportProps={{
            "aria-label": "Template source",
            tabIndex: 0,
          }}
        >
          <Code block>{content}</Code>
        </ScrollArea.Autosize>
        {failure ? (
          <Alert color="red" role="alert" title="Unable to continue template">
            {failure}
          </Alert>
        ) : null}
        {next ? (
          <Button
            loading={loading}
            onClick={() => {
              setFailure("");
              setLoading(true);
              void onLoad(next).then(
                (nextPage) => {
                  const nextContent = scaffoldingPresentation.string(
                    nextPage.properties,
                    "content",
                  );
                  if (nextContent === undefined) {
                    setFailure(
                      "The template continuation returned malformed content.",
                    );
                    setLoading(false);
                    return;
                  }
                  setPage(nextPage);
                  setContent((current) => `${current}${nextContent}`);
                  setLoading(false);
                },
                (reason: unknown) => {
                  setFailure(
                    reason instanceof Error
                      ? reason.message
                      : "Unable to read the next template page.",
                  );
                  setLoading(false);
                },
              );
            }}
            variant="light"
          >
            Load more template content
          </Button>
        ) : (
          <Text c="dimmed" size="sm">
            Complete revision-pinned template loaded.
          </Text>
        )}
      </Stack>
    </Paper>
  );
}

export function TemplateManifestCollection({
  entity,
  onFollow,
  onLoad,
}: SirenEntityProps) {
  const [selection, setSelection] = useState<TemplateSelection>({
    kind: "none",
  });
  const scaffoldingId = scaffoldingPresentation.text(
    entity.properties,
    "scaffolding_id",
  );
  return (
    <ResourcePage
      description="Revision-pinned template paths and their bounded source content."
      title="Templates"
    >
      <Identity label="Scaffolding ID" value={scaffoldingId} />
      <Section title="Template manifest">
        {entity.entities.length ? (
          <Table.ScrollContainer
            minWidth={760}
            scrollAreaProps={{
              viewportProps: { "aria-label": "Template manifest", tabIndex: 0 },
            }}
          >
            <Table highlightOnHover verticalSpacing="sm" withTableBorder>
              <Table.Caption>Revision-pinned template manifest</Table.Caption>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Path</Table.Th>
                  <Table.Th>Write mode</Table.Th>
                  <Table.Th>Size</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {entity.entities.map((item, index) => {
                  const properties =
                    scaffoldingPresentation.itemProperties(item);
                  const target = scaffoldingPresentation.itemTarget(item);
                  const path = scaffoldingPresentation.text(properties, "path");
                  return (
                    <Table.Tr key={`${path}-${index}`}>
                      <Table.Td>
                        <Code>{path}</Code>
                      </Table.Td>
                      <Table.Td>
                        {scaffoldingPresentation.text(properties, "write_mode")}
                      </Table.Td>
                      <Table.Td>
                        {scaffoldingPresentation.text(properties, "size_bytes")}{" "}
                        bytes
                      </Table.Td>
                      <Table.Td>
                        {target.kind === "present" ? (
                          <Button
                            onClick={() => {
                              setSelection({ kind: "loading" });
                              void onLoad(target.target).then(
                                (content) =>
                                  setSelection({
                                    kind: "ready",
                                    entity: content,
                                  }),
                                (reason: unknown) =>
                                  setSelection({
                                    kind: "failed",
                                    message:
                                      reason instanceof Error
                                        ? reason.message
                                        : "Unable to read the template.",
                                  }),
                              );
                            }}
                            size="xs"
                            variant="light"
                          >
                            View template
                          </Button>
                        ) : (
                          <Text c="dimmed" size="sm">
                            Content unavailable
                          </Text>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        ) : (
          <Alert title="No templates">This scaffolding has no templates.</Alert>
        )}
        <SirenContinuation entity={entity} onFollow={onFollow} />
      </Section>
      <Section title="Template source">
        {selection.kind === "none" ? (
          <Text c="dimmed">Choose a template to inspect its source.</Text>
        ) : null}
        {selection.kind === "loading" ? (
          <Group role="status">
            <Loader size="sm" />
            <Text>Loading revision-pinned template…</Text>
          </Group>
        ) : null}
        {selection.kind === "failed" ? (
          <Alert color="red" role="alert" title="Template unavailable">
            {selection.message}
          </Alert>
        ) : null}
        {selection.kind === "ready" ? (
          <TemplateContent entity={selection.entity} onLoad={onLoad} />
        ) : null}
      </Section>
    </ResourcePage>
  );
}
