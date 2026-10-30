import { Button, Group, useComputedColorScheme } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconEye } from "@tabler/icons-react";
import { DiagramPreviewModal } from "./DiagramPreviewModal";
import { MermaidEmbed } from "./MermaidEmbed";
import { DiagramDownload } from "./DiagramDownload";

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
  const colorScheme = useComputedColorScheme();

  return (
    <>
      <Group align="start" gap="xs">
        <Button leftSection={<IconEye aria-hidden size={18} />} onClick={open}>
          Preview diagram
        </Button>
        <DiagramDownload
          diagramId={diagramId}
          presentation="button"
          revision={revision}
          source={source}
          theme={colorScheme === "dark" ? "dark" : "default"}
          title={title}
        />
      </Group>
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
