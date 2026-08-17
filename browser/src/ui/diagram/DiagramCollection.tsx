import {
  Group,
  NativeSelect,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import type { Entity, Target } from "@siren-js/client";
import { useMemo, useState } from "react";
import { DiagramCard, type DiagramSummary } from "./DiagramCard";

export type DiagramCollectionProps = {
  collection: Entity;
  onFollow: (target: Target) => void;
};

export function DiagramCollection({
  collection,
  onFollow,
}: DiagramCollectionProps) {
  const [kind, setKind] = useState("all");
  const [layout, setLayout] = useState("grid");
  const [query, setQuery] = useState("");
  const diagrams = collection.entities as DiagramSummary[];
  const kinds = useMemo(
    () =>
      [...new Set(diagrams.map((diagram) => diagram.properties.kind))].sort(),
    [diagrams],
  );
  const filtered = useMemo(() => {
    const title = query.trim().toLocaleLowerCase();
    return diagrams.filter(
      (diagram) =>
        (kind === "all" || diagram.properties.kind === kind) &&
        diagram.properties.title.toLocaleLowerCase().includes(title),
    );
  }, [diagrams, kind, query]);

  return (
    <Stack>
      <Group align="end">
        <TextInput
          label="Search diagrams"
          onChange={(event) => setQuery(event.currentTarget.value)}
          value={query}
        />
        <NativeSelect
          data={[
            { label: "All kinds", value: "all" },
            ...kinds.map((value) => ({ label: value, value })),
          ]}
          label="Diagram kind"
          onChange={(event) => setKind(event.currentTarget.value)}
          value={kind}
        />
        <SegmentedControl
          aria-label="Gallery layout"
          data={[
            { label: "Grid", value: "grid" },
            { label: "List", value: "list" },
          ]}
          onChange={setLayout}
          value={layout}
        />
      </Group>
      <Text>
        Showing {filtered.length} of {diagrams.length} diagrams
      </Text>
      {filtered.length ? (
        <SimpleGrid
          aria-label={`${layout} diagram gallery`}
          cols={layout === "grid" ? { base: 1, md: 2, xl: 3 } : 1}
          component="section"
        >
          {filtered.map((diagram) => (
            <DiagramCard
              diagram={diagram}
              key={diagram.properties.id}
              onFollow={onFollow}
            />
          ))}
        </SimpleGrid>
      ) : (
        <Text>No diagrams match the current filters.</Text>
      )}
    </Stack>
  );
}
