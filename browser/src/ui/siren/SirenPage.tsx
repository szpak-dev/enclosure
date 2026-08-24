import { Center, Loader, Text } from "@mantine/core";
import type { Action, Entity, Target } from "@siren-js/client";
import { SirenEntity } from "./SirenEntity";

export type SirenPageProps = {
  entity: Entity | null;
  isLoading: boolean;
  onFollow: (target: Target) => void;
  onLoad: (target: Target) => Promise<Entity>;
  onRefresh: () => void;
  onSubmit: (action: Action, values: Record<string, unknown>) => void;
  root: Entity | null;
};

export function SirenPage({
  entity,
  isLoading,
  onFollow,
  onLoad,
  onRefresh,
  onSubmit,
  root,
}: SirenPageProps) {
  if (isLoading || !root)
    return (
      <Center>
        <Loader aria-label="Loading resource" />
      </Center>
    );
  if (!entity) return <Text>No resource selected.</Text>;
  return (
    <SirenEntity
      entity={entity}
      onFollow={onFollow}
      onLoad={onLoad}
      onRefresh={onRefresh}
      onSubmit={onSubmit}
      root={root}
    />
  );
}
