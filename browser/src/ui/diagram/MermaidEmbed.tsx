import { Alert, Box, LoadingOverlay, VisuallyHidden } from "@mantine/core";
import { useEffect, useRef, useState } from "react";
import { MermaidEmbedLoader } from "./MermaidEmbedLoader";

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
  const [loader] = useState(() => new MermaidEmbedLoader());
  const [state, setState] = useState<EmbedState>({ status: "loading" });
  const empty = !source.trim();

  useEffect(() => {
    const container = host.current;
    if (empty || !container) return;

    let current = true;
    let observer: MutationObserver | undefined;
    setState({ status: "loading" });

    void loader.load().then(
      () => {
        if (!current) return;

        const embed = document.createElement("mermaid-embed");
        embed.setAttribute("controls", "1");
        embed.setAttribute("grid", "1");
        embed.setAttribute("height", "calc(100dvh - 5rem)");
        embed.setAttribute("src", "https://mermaid.live/embed");
        embed.setAttribute("title", `${title} Mermaid preview`);
        embed.textContent = source;

        observer = new MutationObserver(() => {
          if (!embed.querySelector("iframe")) return;
          observer?.disconnect();
          if (current) setState({ status: "ready" });
        });
        observer.observe(embed, { childList: true });
        container.replaceChildren(embed);
      },
      (error: Error) => {
        if (current) setState({ message: error.message, status: "error" });
      },
    );

    return () => {
      current = false;
      observer?.disconnect();
      container.replaceChildren();
    };
  }, [diagramId, empty, loader, revision, source, title]);

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
        <Alert color="red" role="alert" title="Unable to load Mermaid preview">
          {state.message}
        </Alert>
      ) : (
        <Box aria-hidden={state.status !== "ready"} h="100%" ref={host} />
      )}
    </Box>
  );
}
