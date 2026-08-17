import { Alert, Box, Center, Loader, Stack, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import { renderMermaidDiagram } from "./MermaidRendererService";

export type DiagramRendererProps = {
  diagramId: string;
  revision: number;
  source: string;
};

type RenderState =
  | { status: "loading" }
  | { status: "rendered"; svg: string }
  | { status: "error"; message: string };

function errorMessage(error: unknown): string {
  return error instanceof Error && error.message.trim()
    ? error.message
    : "Mermaid rejected the diagram source.";
}

export function DiagramRenderer({
  diagramId,
  revision,
  source,
}: DiagramRendererProps) {
  const [state, setState] = useState<RenderState>({ status: "loading" });
  const empty = !source.trim();

  useEffect(() => {
    if (empty) return;
    let current = true;
    setState({ status: "loading" });
    void renderMermaidDiagram(diagramId, revision, source).then(
      (svg) => {
        if (current) setState({ status: "rendered", svg });
      },
      (error: unknown) => {
        if (current)
          setState({ status: "error", message: errorMessage(error) });
      },
    );
    return () => {
      current = false;
    };
  }, [diagramId, empty, revision, source]);

  if (empty)
    return (
      <Alert color="yellow" title="Diagram has no source">
        Add diagram content before opening the rendered view.
      </Alert>
    );

  if (state.status === "loading")
    return (
      <Center mih={240} role="status">
        <Stack align="center" gap="xs">
          <Loader aria-label="Rendering diagram" />
          <Text c="dimmed">Rendering diagram…</Text>
        </Stack>
      </Center>
    );

  if (state.status === "error")
    return (
      <Alert color="red" role="alert" title="Unable to render diagram">
        {state.message}
      </Alert>
    );

  return (
    <Box
      aria-label="Rendered diagram"
      dangerouslySetInnerHTML={{ __html: state.svg }}
      mih="12rem"
      role="img"
      style={{ overflow: "auto", textAlign: "center" }}
    />
  );
}
