import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import type { EmbeddedEntity, Entity, Target } from "@siren-js/client";
import { DiagramPreview } from "./DiagramPreview";
import { DiagramPreviewErrorBoundary } from "./DiagramPreviewErrorBoundary";

export type DiagramSummaryProperties = Entity["properties"] & {
  id: string;
  kind: string;
  revision: number;
  title: string;
};

export type DiagramSummary = EmbeddedEntity<DiagramSummaryProperties>;

export type DiagramCardProps = {
  diagram: DiagramSummary;
  onFollow: (target: Target) => void;
  onLoad: (target: Target) => Promise<Entity>;
};

export function DiagramCard({ diagram, onFollow, onLoad }: DiagramCardProps) {
  const target = diagram.links.find((link) => link.rel.includes("self"));

  return (
    <Card component="article" aria-label={diagram.properties.title} withBorder>
      <Stack gap="xs">
        <Group justify="space-between">
          <Title order={2}>{diagram.properties.title}</Title>
          <Badge>{diagram.properties.kind}</Badge>
        </Group>
        <Text c="dimmed" size="sm">
          Revision {diagram.properties.revision}
        </Text>
        {target ? (
          <>
            <DiagramPreviewErrorBoundary>
              <DiagramPreview
                onLoad={onLoad}
                target={target}
                title={diagram.properties.title}
              />
            </DiagramPreviewErrorBoundary>
            <Button
              component="a"
              href={`#${target.href}`}
              onClick={(event) => {
                event.preventDefault();
                onFollow(target);
              }}
              variant="light"
            >
              Open diagram
            </Button>
          </>
        ) : (
          <Alert color="red" role="alert" title="Diagram link unavailable">
            This diagram summary has no self relationship.
          </Alert>
        )}
      </Stack>
    </Card>
  );
}
