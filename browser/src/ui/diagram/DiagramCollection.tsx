import { Group, List, Stack, Text } from "@mantine/core";
import type { Entity, Target } from "@siren-js/client";
import { SirenContinuation } from "../siren/SirenContinuation";
import {
  DiagramOrderingControls,
  type DiagramCollectionProperties,
} from "./DiagramOrderingControls";
import { DiagramListItem, type DiagramSummary } from "./DiagramListItem";

export type DiagramCollectionProps = {
  collection: Entity<DiagramCollectionProperties>;
  onFollow: (target: Target) => void;
  onLoad: (target: Target) => Promise<Entity>;
};

export function DiagramCollection({
  collection,
  onFollow,
  onLoad,
}: DiagramCollectionProps) {
  const diagrams = collection.entities as DiagramSummary[];

  return (
    <Stack>
      <Group align="end">
        <DiagramOrderingControls collection={collection} onFollow={onFollow} />
      </Group>
      <Text>
        {diagrams.length} {diagrams.length === 1 ? "diagram" : "diagrams"}
      </Text>
      {diagrams.length ? (
        <List aria-label="Diagrams" listStyleType="none" spacing="xs">
          {diagrams.map((diagram) => {
            return (
              <List.Item key={diagram.properties.id}>
                <DiagramListItem
                  diagram={diagram}
                  onFollow={onFollow}
                  onLoad={onLoad}
                />
              </List.Item>
            );
          })}
        </List>
      ) : (
        <Text>This diagram set has no diagrams.</Text>
      )}
      <SirenContinuation entity={collection} onFollow={onFollow} />
    </Stack>
  );
}
