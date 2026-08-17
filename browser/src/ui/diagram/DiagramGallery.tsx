import { Alert, Button, Paper, Stack, Text, Title } from "@mantine/core";
import type { Entity, Link } from "@siren-js/client";
import { useCallback, useEffect, useState } from "react";
import { SirenActions } from "../siren/SirenActions";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { DiagramCollection } from "./DiagramCollection";

type DiagramSetProperties = Entity["properties"] & {
  description: string;
  title: string;
};

export type DiagramGalleryProps = SirenEntityProps & {
  collectionTarget: Link;
};

export function DiagramGallery({
  collectionTarget,
  entity,
  onFollow,
  onLoad,
  onSubmit,
}: DiagramGalleryProps) {
  const [collection, setCollection] = useState<Entity | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const properties = entity.properties as DiagramSetProperties;

  const loadCollection = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      setCollection(await onLoad(collectionTarget));
    } catch (reason) {
      setError(reason as Error);
    } finally {
      setIsLoading(false);
    }
  }, [collectionTarget, onLoad]);

  useEffect(() => {
    void loadCollection();
  }, [loadCollection]);

  return (
    <Paper component="article" aria-label={properties.title} p="md" shadow="xs">
      <Stack>
        <div>
          <Title order={1}>{properties.title}</Title>
          {properties.description ? (
            <Text c="dimmed">{properties.description}</Text>
          ) : null}
        </div>

        {error ? (
          <Alert color="red" role="alert" title="Unable to load diagrams">
            <Stack gap="xs">
              {error.message}
              <Button
                onClick={() => void loadCollection()}
                size="xs"
                variant="light"
              >
                Retry
              </Button>
            </Stack>
          </Alert>
        ) : null}

        {isLoading ? (
          <Text role="status">Loading diagrams…</Text>
        ) : collection ? (
          <DiagramCollection collection={collection} onFollow={onFollow} />
        ) : null}

        <SirenActions
          actions={entity.actions}
          onSubmit={onSubmit}
          values={entity.properties}
        />
      </Stack>
    </Paper>
  );
}
