import { Group, List, Paper, Stack, Text, Title } from "@mantine/core";
import type { Action, Entity, Target } from "@siren-js/client";
import {
  DiagramOrderingControls,
  isOrderedDiagramCollection,
} from "../diagram/DiagramOrderingControls";
import { DiagramListItem, isDiagramSummary } from "../diagram/DiagramListItem";
import { SirenCollectionItem } from "./SirenCollectionItem";
import { SirenContinuation } from "./SirenContinuation";
import { SirenActions } from "./SirenActions";
import { collectionLabel, itemTitle } from "./SirenLabels";

export type SirenCollectionProps = {
  entity: Entity;
  onFollow: (target: Target) => void;
  onLoad: (target: Target) => Promise<Entity>;
  onSubmit: (action: Action, values: Record<string, unknown>) => void;
};

export function SirenCollection({
  entity,
  onFollow,
  onLoad,
  onSubmit,
}: SirenCollectionProps) {
  const label = collectionLabel(entity);
  const titleCounts = new Map<string, number>();
  entity.entities.forEach((item) => {
    const itemLabel = itemTitle(item);
    if (itemLabel)
      titleCounts.set(itemLabel, (titleCounts.get(itemLabel) ?? 0) + 1);
  });

  return (
    <Paper component="section" aria-label={label} p="md" shadow="xs">
      <Stack>
        <Title order={1}>{label}</Title>
        {isOrderedDiagramCollection(entity) ? (
          <Group align="end">
            <DiagramOrderingControls collection={entity} onFollow={onFollow} />
          </Group>
        ) : null}
        {entity.entities.length ? (
          <List
            listStyleType="none"
            spacing="xs"
            styles={{
              itemWrapper: { width: "100%" },
              itemLabel: { width: "100%" },
            }}
          >
            {entity.entities.map((item, index) => (
              <List.Item key={`${item.rel.join("-")}-${index}`}>
                {isDiagramSummary(item) ? (
                  <DiagramListItem
                    diagram={item}
                    onFollow={onFollow}
                    onLoad={onLoad}
                  />
                ) : (
                  <SirenCollectionItem
                    ambiguousTitle={
                      (titleCounts.get(itemTitle(item) ?? "") ?? 0) > 1
                    }
                    index={index}
                    item={item}
                    onFollow={onFollow}
                  />
                )}
              </List.Item>
            ))}
          </List>
        ) : (
          <Text c="dimmed">No resources available.</Text>
        )}
        <SirenContinuation entity={entity} onFollow={onFollow} />
        <SirenActions actions={entity.actions} onSubmit={onSubmit} />
      </Stack>
    </Paper>
  );
}
