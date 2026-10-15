import { ActionIcon, Tooltip } from "@mantine/core";
import type { Entity, Target } from "@siren-js/client";
import { useDisclosure } from "@mantine/hooks";
import { IconEye } from "@tabler/icons-react";
import { useState } from "react";
import type { DiagramProperties } from "./DiagramEntity";
import { DiagramPreviewContent } from "./DiagramPreviewContent";
import { DiagramPreviewModal } from "./DiagramPreviewModal";

export type DiagramPreviewProps = {
  onLoad: (target: Target) => Promise<Entity>;
  target: Target;
  title: string;
};

type PreviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "loaded"; entity: Entity }
  | { status: "error"; error: Error };

export function DiagramPreview({ onLoad, target, title }: DiagramPreviewProps) {
  const [opened, { close, open }] = useDisclosure(false);
  const [state, setState] = useState<PreviewState>({ status: "idle" });

  const load = () => {
    setState({ status: "loading" });
    void onLoad(target).then(
      (entity) => {
        setState({ status: "loaded", entity });
      },
      (error: Error) => {
        setState({ status: "error", error });
      },
    );
  };

  const showPreview = () => {
    open();
    if (state.status === "idle") load();
  };

  let preview;
  if (state.status === "idle" || state.status === "loading") {
    preview = <DiagramPreviewContent status="loading" title={title} />;
  } else if (state.status === "error") {
    preview = (
      <DiagramPreviewContent
        message={state.error.message}
        onRetry={load}
        status="error"
      />
    );
  } else {
    const properties = state.entity.properties as DiagramProperties;
    preview = (
      <DiagramPreviewContent
        diagramId={properties.id}
        revision={properties.revision}
        source={properties.source}
        status="ready"
        title={properties.title}
      />
    );
  }

  return (
    <>
      <Tooltip label={`Preview ${title}`}>
        <ActionIcon
          aria-label={`Preview ${title}`}
          onClick={showPreview}
          size="lg"
          variant="subtle"
        >
          <IconEye aria-hidden size={20} />
        </ActionIcon>
      </Tooltip>
      <DiagramPreviewModal onClose={close} opened={opened} title={title}>
        {preview}
      </DiagramPreviewModal>
    </>
  );
}
