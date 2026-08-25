import { Paper, Stack, Title } from "@mantine/core";
import type { Action, Entity, Target } from "@siren-js/client";
import { sirenRegistry } from "./SirenRegistry";
import { SirenActions } from "./SirenActions";
import { SirenCollection } from "./SirenCollection";
import { SirenProperties } from "./SirenProperties";
import { SirenRelatedResources } from "./SirenRelatedResources";
import { entityLabel } from "./SirenLabels";
import { relatedResources } from "./SirenNavigationModel";

export type SirenEntityProps = {
  entity: Entity;
  onFollow: (target: Target) => void;
  onLoad: (target: Target) => Promise<Entity>;
  onRefresh: () => void;
  onSubmit: (action: Action, values: Record<string, unknown>) => void;
  root: Entity;
};

export function SirenEntity({
  entity,
  onFollow,
  onLoad,
  onRefresh,
  onSubmit,
  root,
}: SirenEntityProps) {
  if (entity.class.includes("collection")) {
    return (
      <SirenCollection
        entity={entity}
        onFollow={onFollow}
        onSubmit={onSubmit}
      />
    );
  }

  const EntityComponent = sirenRegistry.entities.resolve(entity.class);

  if (EntityComponent) {
    return (
      <EntityComponent
        entity={entity}
        onFollow={onFollow}
        onLoad={onLoad}
        onRefresh={onRefresh}
        onSubmit={onSubmit}
        root={root}
      />
    );
  }

  const label = entityLabel(entity);

  return (
    <Paper component="article" aria-label={label} p="md" shadow="xs">
      <Stack>
        <Title order={1}>{label}</Title>
        <SirenProperties entity={entity} />
        <SirenRelatedResources
          onFollow={onFollow}
          resources={relatedResources(entity)}
        />
        <SirenActions
          actions={entity.actions}
          onSubmit={onSubmit}
          values={entity.properties}
        />
      </Stack>
    </Paper>
  );
}
