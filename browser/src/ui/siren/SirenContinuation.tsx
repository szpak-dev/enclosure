import { Button, Group, Text } from "@mantine/core";
import type { Entity, Target } from "@siren-js/client";
import { linkLabel } from "./SirenLabels";

export type SirenContinuationProps = {
  entity: Entity;
  onFollow: (target: Target) => void;
};

export function SirenContinuation({
  entity,
  onFollow,
}: SirenContinuationProps) {
  const previous = entity.links.find((link) =>
    link.rel.some((relation) => relation === "previous" || relation === "prev"),
  );
  const next = entity.links.find((link) => link.rel.includes("next"));
  const limit = Object.entries(entity.properties).find(
    ([name]) => name === "limit",
  )?.[1];
  const pageSize =
    typeof limit === "number" || typeof limit === "string"
      ? String(limit)
      : undefined;
  if (!previous && !next && !pageSize) return null;

  return (
    <Group justify="space-between">
      {pageSize ? (
        <Text c="dimmed" size="sm">
          Page size: {pageSize}
        </Text>
      ) : (
        <span />
      )}
      <Group>
        {previous ? (
          <Button
            component="a"
            href={`#${previous.href}`}
            onClick={(event) => {
              event.preventDefault();
              onFollow(previous);
            }}
            variant="default"
          >
            {linkLabel(previous)}
          </Button>
        ) : null}
        {next ? (
          <Button
            component="a"
            href={`#${next.href}`}
            onClick={(event) => {
              event.preventDefault();
              onFollow(next);
            }}
            variant="light"
          >
            {linkLabel(next)}
          </Button>
        ) : null}
      </Group>
    </Group>
  );
}
