import { Alert, Box, Text } from "@mantine/core";
import type { Entity, Target } from "@siren-js/client";
import { useEffect, useState } from "react";
import type { DiagramProperties } from "./DiagramEntity";
import { DiagramRenderer } from "./DiagramRenderer";
import { useElementVisibility } from "./useElementVisibility";

export type DiagramPreviewProps = {
  onLoad: (target: Target) => Promise<Entity>;
  target: Target;
  title: string;
};

type PreviewState =
  | { status: "waiting" }
  | { status: "loading" }
  | { status: "loaded"; entity: Entity }
  | { status: "error"; error: Error };

export function DiagramPreview({ onLoad, target, title }: DiagramPreviewProps) {
  const { ref, visible } = useElementVisibility<HTMLDivElement>();
  const [state, setState] = useState<PreviewState>({ status: "waiting" });

  useEffect(() => {
    if (!visible) return;

    let current = true;
    setState({ status: "loading" });
    void onLoad(target).then(
      (entity) => {
        if (current) setState({ status: "loaded", entity });
      },
      (error: Error) => {
        if (current) setState({ status: "error", error });
      },
    );

    return () => {
      current = false;
    };
  }, [onLoad, target, visible]);

  let preview;
  if (state.status === "waiting") {
    preview = <Text c="dimmed">Preview loads when this card is visible.</Text>;
  } else if (state.status === "loading") {
    preview = <Text role="status">Loading {title}…</Text>;
  } else if (state.status === "error") {
    preview = (
      <Alert color="red" role="alert" title="Unable to load diagram preview">
        {state.error.message}
      </Alert>
    );
  } else {
    const properties = state.entity.properties as DiagramProperties;
    preview = (
      <DiagramRenderer
        diagramId={properties.id}
        revision={properties.revision}
        source={properties.source}
      />
    );
  }

  return (
    <Box aria-label={`${title} preview`} ref={ref}>
      {preview}
    </Box>
  );
}
