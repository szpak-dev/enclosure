import { Alert, Box, Group, NavLink } from "@mantine/core";
import type {
  EmbeddedEntity,
  Entity,
  SubEntity,
  Target,
} from "@siren-js/client";
import { RelativeTime } from "../time/RelativeTime";
import { DiagramPreview } from "./DiagramPreview";

export type DiagramSummaryProperties = Entity["properties"] & {
  id: string;
  kind: string;
  revision: number;
  title: string;
  updated_at: string;
};

export type DiagramSummary = EmbeddedEntity<DiagramSummaryProperties>;

export type DiagramListItemProps = {
  diagram: DiagramSummary;
  onFollow: (target: Target) => void;
  onLoad: (target: Target) => Promise<Entity>;
};

export function isDiagramSummary(item: SubEntity): item is DiagramSummary {
  return item.class.includes("diagram");
}

export function DiagramListItem({
  diagram,
  onFollow,
  onLoad,
}: DiagramListItemProps) {
  const target = diagram.links.find((link) => link.rel.includes("self"));

  if (!target)
    return (
      <Alert color="red" title={diagram.properties.title}>
        Diagram details and preview are unavailable because this item has no
        self relationship.
      </Alert>
    );

  return (
    <Group gap="xs" wrap="nowrap">
      <Box flex={1}>
        <NavLink
          component="a"
          description={
            <Group component="span" gap="xs" wrap="wrap">
              <span>{diagram.properties.kind}</span>
              <RelativeTime
                prefix="Updated "
                timestamp={diagram.properties.updated_at}
              />
            </Group>
          }
          href={`#${target.href}`}
          label={diagram.properties.title}
          onClick={(event) => {
            event.preventDefault();
            onFollow(target);
          }}
        />
      </Box>
      <DiagramPreview
        onLoad={onLoad}
        target={target}
        title={diagram.properties.title}
      />
    </Group>
  );
}
