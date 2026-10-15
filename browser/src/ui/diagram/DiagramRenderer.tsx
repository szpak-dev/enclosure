import { Button } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconEye } from "@tabler/icons-react";
import { DiagramPreviewModal } from "./DiagramPreviewModal";
import { MermaidEmbed } from "./MermaidEmbed";

export type DiagramRendererProps = {
  diagramId: string;
  revision: number;
  source: string;
  title: string;
};

export function DiagramRenderer({
  diagramId,
  revision,
  source,
  title,
}: DiagramRendererProps) {
  const [opened, { close, open }] = useDisclosure(false);

  return (
    <>
      <Button leftSection={<IconEye aria-hidden size={18} />} onClick={open}>
        Preview diagram
      </Button>
      <DiagramPreviewModal onClose={close} opened={opened} title={title}>
        <MermaidEmbed
          diagramId={diagramId}
          revision={revision}
          source={source}
          title={title}
        />
      </DiagramPreviewModal>
    </>
  );
}
