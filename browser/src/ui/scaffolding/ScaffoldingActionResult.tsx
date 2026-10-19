import {
  Alert,
  Badge,
  Button,
  Card,
  Code,
  Group,
  Paper,
  ScrollArea,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import type { Action, Entity, Target } from "@siren-js/client";
import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { Identity, PropertyTable } from "../resource/ResourcePrimitives";
import { useSirenActionExecution } from "../siren/SirenActionExecution";
import { ScaffoldingCards } from "./ScaffoldingCards";
import { scaffoldingPresentation } from "./ScaffoldingPresentation";

export type ScaffoldingRenderingActions =
  { kind: "unavailable" } | { kind: "available"; read: Action; render: Action };

export type ScaffoldingActionResultProps = {
  actionName: string;
  entity: Entity;
  onFollow: (target: Target) => void;
  renderingActions?: ScaffoldingRenderingActions;
  values: Record<string, unknown>;
};

type RenderedContent =
  | { kind: "none" }
  | { kind: "loading" }
  | { kind: "failed"; message: string }
  | { kind: "ready"; content: string; entity: Entity };

type RenderingResultProps = {
  actions: ScaffoldingRenderingActions;
  entity: Entity;
  values: Record<string, unknown>;
};

type RenderingPages = {
  current: Entity;
  loaded: readonly Entity[];
};

function RenderingResult({ actions, entity, values }: RenderingResultProps) {
  const execution = useSirenActionExecution();
  const [pages, setPages] = useState<RenderingPages>({
    current: entity,
    loaded: [entity],
  });
  const [loadingPage, setLoadingPage] = useState(false);
  const [pageFailure, setPageFailure] = useState("");
  const [content, setContent] = useState<RenderedContent>({ kind: "none" });
  const files = pages.loaded.flatMap((page) =>
    scaffoldingPresentation.renderedFiles(page.properties),
  );
  const hasMore = scaffoldingPresentation.boolean(
    pages.current.properties,
    "has_more",
  );
  const pageLimit = scaffoldingPresentation.integer(
    pages.current.properties,
    "limit",
  );
  const nextPageOffset = scaffoldingPresentation.integer(
    pages.current.properties,
    "next_offset",
  );
  const canLoadMore =
    hasMore === true && pageLimit !== undefined && nextPageOffset !== undefined;
  const parameters = values.parameters;

  useEffect(() => {
    setPages({ current: entity, loaded: [entity] });
    setPageFailure("");
    setContent({ kind: "none" });
  }, [entity]);

  if (actions.kind === "unavailable" || execution.kind === "unavailable")
    return (
      <Alert color="red" title="Rendering controls unavailable">
        The rendering result cannot advertise follow-up reads on this surface.
      </Alert>
    );

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={3}>Rendered files</Title>
        <Badge variant="light">{files.length} loaded</Badge>
      </Group>
      {files.length ? (
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          {files.map((file, index) => (
            <Card key={`${file.path}-${index}`} padding="lg" withBorder>
              <Stack justify="space-between" mih={210}>
                <Stack gap="xs">
                  <Code>{file.path}</Code>
                  <Text c="dimmed" size="sm">
                    {file.sizeBytes} bytes ·{" "}
                    {file.overwrite ? "may overwrite" : "create only"}
                  </Text>
                  <Code block>{file.preview || "Empty rendered file"}</Code>
                </Stack>
                <Button
                  onClick={() => {
                    setContent({ kind: "loading" });
                    void execution
                      .execute(actions.read, {
                        expected_revision: file.revision,
                        limit: 1000,
                        offset: 0,
                        parameters,
                        path: file.path,
                      })
                      .then(
                        (response) => {
                          if (response.kind === "empty") {
                            setContent({
                              kind: "failed",
                              message:
                                "The rendered-file read returned no document.",
                            });
                            return;
                          }
                          const returnedContent =
                            scaffoldingPresentation.string(
                              response.entity.properties,
                              "content",
                            );
                          if (returnedContent === undefined) {
                            setContent({
                              kind: "failed",
                              message:
                                "The rendered-file read returned malformed content.",
                            });
                            return;
                          }
                          setContent({
                            content: returnedContent,
                            entity: response.entity,
                            kind: "ready",
                          });
                        },
                        (reason: unknown) =>
                          setContent({
                            kind: "failed",
                            message:
                              reason instanceof Error
                                ? reason.message
                                : "Unable to read rendered content.",
                          }),
                      );
                  }}
                  variant="light"
                >
                  View rendered file
                </Button>
              </Stack>
            </Card>
          ))}
        </SimpleGrid>
      ) : (
        <Alert title="No rendered files">
          This scaffolding produced an empty source package.
        </Alert>
      )}
      {pageFailure ? (
        <Alert color="red" role="alert" title="Unable to continue rendering">
          {pageFailure}
        </Alert>
      ) : null}
      {hasMore === true && !canLoadMore ? (
        <Alert color="red.9" title="Rendering continuation unavailable">
          The server reported more rendered files without a complete limit and
          next offset.
        </Alert>
      ) : null}
      {canLoadMore ? (
        <Button
          loading={loadingPage}
          onClick={() => {
            setLoadingPage(true);
            setPageFailure("");
            void execution
              .execute(actions.render, {
                limit: pageLimit,
                offset: nextPageOffset,
                parameters,
              })
              .then(
                (response) => {
                  if (response.kind === "empty") {
                    setPageFailure("The next rendering page was empty.");
                  } else {
                    setPages((currentPages) => ({
                      current: response.entity,
                      loaded: [...currentPages.loaded, response.entity],
                    }));
                  }
                  setLoadingPage(false);
                },
                (reason: unknown) => {
                  setPageFailure(
                    reason instanceof Error
                      ? reason.message
                      : "Unable to read the next rendering page.",
                  );
                  setLoadingPage(false);
                },
              );
          }}
          variant="default"
        >
          Load more rendered files
        </Button>
      ) : null}
      {content.kind === "loading" ? (
        <Text role="status">Loading rendered content…</Text>
      ) : null}
      {content.kind === "failed" ? (
        <Alert color="red" role="alert" title="Rendered content unavailable">
          {content.message}
        </Alert>
      ) : null}
      {content.kind === "ready" ? (
        <RenderedContentPanel
          actions={actions}
          content={content}
          parameters={parameters}
          setContent={setContent}
        />
      ) : null}
    </Stack>
  );
}

type RenderedContentPanelProps = {
  actions: Extract<ScaffoldingRenderingActions, { kind: "available" }>;
  content: Extract<RenderedContent, { kind: "ready" }>;
  parameters: unknown;
  setContent: Dispatch<SetStateAction<RenderedContent>>;
};

function RenderedContentPanel({
  actions,
  content,
  parameters,
  setContent,
}: RenderedContentPanelProps) {
  const execution = useSirenActionExecution();
  const nextOffset = scaffoldingPresentation.integer(
    content.entity.properties,
    "next_offset",
  );
  const hasMore = scaffoldingPresentation.boolean(
    content.entity.properties,
    "has_more",
  );
  const limit = scaffoldingPresentation.integer(
    content.entity.properties,
    "limit",
  );
  const revision = scaffoldingPresentation.string(
    content.entity.properties,
    "revision",
  );
  const path = scaffoldingPresentation.string(
    content.entity.properties,
    "path",
  );
  const canLoadMore =
    hasMore === true &&
    execution.kind === "available" &&
    nextOffset !== undefined &&
    limit !== undefined &&
    revision !== undefined &&
    path !== undefined;
  return (
    <Paper p="lg" radius="md" withBorder>
      <Stack>
        <Title order={3} size="h4">
          {scaffoldingPresentation.text(content.entity.properties, "path")}
        </Title>
        <Identity
          label="Rendered revision"
          value={scaffoldingPresentation.text(
            content.entity.properties,
            "revision",
          )}
        />
        <ScrollArea.Autosize
          mah="32rem"
          type="auto"
          viewportProps={{
            "aria-label": "Rendered file content",
            tabIndex: 0,
          }}
        >
          <Code block>{content.content}</Code>
        </ScrollArea.Autosize>
        {canLoadMore ? (
          <Button
            onClick={() => {
              void execution
                .execute(actions.read, {
                  expected_revision: revision,
                  limit,
                  offset: nextOffset,
                  parameters,
                  path,
                })
                .then(
                  (response) => {
                    if (response.kind === "empty") {
                      setContent({
                        kind: "failed",
                        message:
                          "The rendered-file continuation returned no document.",
                      });
                      return;
                    }
                    const returnedContent = scaffoldingPresentation.string(
                      response.entity.properties,
                      "content",
                    );
                    if (returnedContent === undefined) {
                      setContent({
                        kind: "failed",
                        message:
                          "The rendered-file continuation returned malformed content.",
                      });
                      return;
                    }
                    setContent({
                      content: `${content.content}${returnedContent}`,
                      entity: response.entity,
                      kind: "ready",
                    });
                  },
                  (reason: unknown) =>
                    setContent({
                      kind: "failed",
                      message:
                        reason instanceof Error
                          ? reason.message
                          : "Unable to continue rendered content.",
                    }),
                );
            }}
            variant="light"
          >
            Load more rendered content
          </Button>
        ) : hasMore === false ? (
          <Text c="dimmed" size="sm">
            Complete rendered file loaded.
          </Text>
        ) : (
          <Alert color="red.9" title="Content continuation unavailable">
            The server did not provide complete continuation metadata for this
            rendered file.
          </Alert>
        )}
      </Stack>
    </Paper>
  );
}

export function ScaffoldingActionResult({
  actionName,
  entity,
  onFollow,
  renderingActions = { kind: "unavailable" },
  values,
}: ScaffoldingActionResultProps) {
  if (actionName === "search_scaffoldings")
    return <ScaffoldingCards items={entity.entities} onFollow={onFollow} />;
  if (actionName === "render_scaffolding")
    return (
      <RenderingResult
        actions={renderingActions}
        entity={entity}
        values={values}
      />
    );
  if (
    actionName === "delete_scaffolding" &&
    scaffoldingPresentation.string(entity.properties, "reason_code") ===
      "destructive_approval_required"
  )
    return (
      <Stack>
        <Identity
          label="Approval request ID"
          value={scaffoldingPresentation.text(
            entity.properties,
            "approval_request_id",
          )}
        />
        <PropertyTable
          caption="Pending one-time approval"
          label={(name) => scaffoldingPresentation.label(name)}
          properties={entity.properties}
          text={(properties, name) =>
            scaffoldingPresentation.text(properties, name)
          }
          visible={["reason_code", "execution_id", "expires_at"]}
        />
      </Stack>
    );
  return (
    <Stack>
      <Title order={3}>{entity.title || "Scaffolding result"}</Title>
      <PropertyTable
        caption="Scaffolding result"
        label={(name) => scaffoldingPresentation.label(name)}
        properties={entity.properties}
        text={(properties, name) =>
          scaffoldingPresentation.text(properties, name)
        }
        visible={["name", "language_id", "description", "template_count"]}
      />
      {entity.links
        .filter((link) => link.rel.includes("self"))
        .map((link) => (
          <Button
            component="a"
            href={`#${link.href}`}
            key={link.href.toString()}
            onClick={(event) => {
              event.preventDefault();
              onFollow(link);
            }}
            variant="light"
          >
            Open scaffolding
          </Button>
        ))}
    </Stack>
  );
}
