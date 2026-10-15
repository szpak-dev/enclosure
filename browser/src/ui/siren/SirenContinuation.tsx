import { Button, Group } from "@mantine/core";
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
  const next = entity.links.find((link) => link.rel.includes("next"));
  if (!next) return null;

  return (
    <Group justify="flex-end">
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
    </Group>
  );
}
