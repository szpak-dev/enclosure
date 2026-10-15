import { Alert, Button, Center, Loader, Stack, Text } from "@mantine/core";
import { MermaidEmbed } from "./MermaidEmbed";

type DiagramPreviewLoading = {
  status: "loading";
  title: string;
};

type DiagramPreviewFailure = {
  message: string;
  onRetry: () => void;
  status: "error";
};

type DiagramPreviewReady = {
  diagramId: string;
  revision: number;
  source: string;
  status: "ready";
  title: string;
};

export type DiagramPreviewContentProps =
  DiagramPreviewLoading | DiagramPreviewFailure | DiagramPreviewReady;

export function DiagramPreviewContent(props: DiagramPreviewContentProps) {
  if (props.status === "loading")
    return (
      <Center h="100%">
        <Stack align="center" gap="xs">
          <Loader aria-hidden />
          <Text role="status">Loading {props.title}…</Text>
        </Stack>
      </Center>
    );

  if (props.status === "error")
    return (
      <Alert color="red" role="alert" title="Unable to load diagram preview">
        <Stack gap="xs">
          <Text>{props.message}</Text>
          <Button onClick={props.onRetry} variant="light">
            Retry
          </Button>
        </Stack>
      </Alert>
    );

  return (
    <MermaidEmbed
      diagramId={props.diagramId}
      revision={props.revision}
      source={props.source}
      title={props.title}
    />
  );
}
