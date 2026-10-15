import { Box, Modal } from "@mantine/core";
import type { PropsWithChildren } from "react";

export type DiagramPreviewModalProps = PropsWithChildren<{
  onClose: () => void;
  opened: boolean;
  title: string;
}>;

export function DiagramPreviewModal({
  children,
  onClose,
  opened,
  title,
}: DiagramPreviewModalProps) {
  return (
    <Modal
      closeButtonProps={{ "aria-label": `Close ${title} preview` }}
      fullScreen
      onClose={onClose}
      opened={opened}
      title={`${title} preview`}
    >
      <Box h="calc(100dvh - 5rem)">{children}</Box>
    </Modal>
  );
}
