import {
  Alert,
  Box,
  LoadingOverlay,
  useComputedColorScheme,
  VisuallyHidden,
} from "@mantine/core";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { MermaidRenderer, type MermaidTheme } from "./MermaidRenderer";
import { MermaidViewport } from "./MermaidViewport";

export type MermaidEmbedProps = {
  diagramId: string;
  revision: number;
  source: string;
  title: string;
};

type EmbedState =
  | { status: "loading" }
  | { status: "ready" }
  | { message: string; status: "error" };

export function MermaidEmbed({
  diagramId,
  revision,
  source,
  title,
}: MermaidEmbedProps) {
  const host = useRef<HTMLDivElement>(null);
  const renderingId = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const colorScheme = useComputedColorScheme();
  const theme: MermaidTheme = colorScheme === "dark" ? "dark" : "default";
  const renderer = useMemo(() => new MermaidRenderer(theme), [theme]);
  const [state, setState] = useState<EmbedState>({ status: "loading" });
  const empty = !source.trim();

  useEffect(() => {
    const container = host.current;
    if (empty || !container) return;

    let current = true;
    setState({ status: "loading" });
    container.replaceChildren();

    void renderer.render(source, `mermaid-${renderingId}`).then(
      (rendering) => {
        if (!current) return;

        try {
          renderer.mount(container, rendering);
          setState({ status: "ready" });
        } catch (error: unknown) {
          setState({
            message:
              error instanceof Error
                ? error.message
                : "Mermaid could not render the diagram.",
            status: "error",
          });
        }
      },
      (error: unknown) => {
        if (!current) return;
        setState({
          message:
            error instanceof Error
              ? error.message
              : "Mermaid could not render the diagram.",
          status: "error",
        });
      },
    );

    return () => {
      current = false;
      container.replaceChildren();
    };
  }, [diagramId, empty, renderer, renderingId, revision, source]);

  if (empty)
    return (
      <Alert color="gray" title="Diagram has no source">
        Add diagram content before opening the preview.
      </Alert>
    );

  return (
    <Box h="100%" pos="relative">
      <LoadingOverlay
        loaderProps={{ "aria-hidden": true }}
        visible={state.status === "loading"}
      />
      {state.status === "loading" ? (
        <VisuallyHidden role="status">Loading Mermaid preview</VisuallyHidden>
      ) : null}
      {state.status === "error" ? (
        <Alert
          color="red"
          role="alert"
          title="Unable to render Mermaid preview"
          pos="absolute"
          style={{ zIndex: 3 }}
        >
          {state.message}
        </Alert>
      ) : null}
      <MermaidViewport
        host={host}
        key={`${diagramId}:${revision}:${theme}`}
        ready={state.status === "ready"}
        title={title}
      />
    </Box>
  );
}
