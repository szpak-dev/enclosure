import { Alert, Input, SegmentedControl, Select } from "@mantine/core";
import type { Entity, Target } from "@siren-js/client";

export enum DiagramOrderField {
  CreatedAt = "created_at",
  Title = "title",
  UpdatedAt = "updated_at",
}

export enum DiagramSortDirection {
  Ascending = "asc",
  Descending = "desc",
}

export type DiagramCollectionProperties = {
  direction: DiagramSortDirection;
  has_more: boolean;
  limit: number;
  next_offset: number;
  order_by: DiagramOrderField;
};

export type DiagramOrderingControlsProps = {
  collection: Entity<DiagramCollectionProperties>;
  onFollow: (target: Target) => void;
};

const orderFields = [
  { label: "Created", value: DiagramOrderField.CreatedAt },
  { label: "Title", value: DiagramOrderField.Title },
  { label: "Updated", value: DiagramOrderField.UpdatedAt },
];

const directions = [
  { label: "Ascending", value: DiagramSortDirection.Ascending },
  { label: "Descending", value: DiagramSortDirection.Descending },
];

function orderField(value: string | null): DiagramOrderField {
  switch (value) {
    case DiagramOrderField.CreatedAt:
      return DiagramOrderField.CreatedAt;
    case DiagramOrderField.Title:
      return DiagramOrderField.Title;
    case DiagramOrderField.UpdatedAt:
      return DiagramOrderField.UpdatedAt;
    default:
      throw new Error("Diagram ordering field is unavailable.");
  }
}

function sortDirection(value: string): DiagramSortDirection {
  switch (value) {
    case DiagramSortDirection.Ascending:
      return DiagramSortDirection.Ascending;
    case DiagramSortDirection.Descending:
      return DiagramSortDirection.Descending;
    default:
      throw new Error("Diagram ordering direction is unavailable.");
  }
}

function orderingTarget(
  collection: Entity<DiagramCollectionProperties>,
  orderBy: DiagramOrderField,
  direction: DiagramSortDirection,
): string {
  const self = collection.links.find((link) => link.rel.includes("self"));
  if (!self) throw new Error("Diagram collection has no self relationship.");

  const target = new URL(self.href, window.location.origin);
  target.searchParams.set("offset", "0");
  target.searchParams.set("limit", String(collection.properties.limit));
  target.searchParams.set("order_by", orderBy);
  target.searchParams.set("direction", direction);
  return `${target.pathname}${target.search}${target.hash}`;
}

export function isOrderedDiagramCollection(
  entity: Entity,
): entity is Entity<DiagramCollectionProperties> {
  return (
    entity.class.includes("collection") &&
    (entity.class.includes("diagram") || entity.class.includes("diagram-set"))
  );
}

export function DiagramOrderingControls({
  collection,
  onFollow,
}: DiagramOrderingControlsProps) {
  if (!collection.links.some((link) => link.rel.includes("self")))
    return (
      <Alert color="red" title="Diagram ordering unavailable">
        This diagram collection has no self relationship.
      </Alert>
    );

  return (
    <>
      <Select
        allowDeselect={false}
        data={orderFields}
        label="Sort by"
        onChange={(value) =>
          onFollow(
            orderingTarget(
              collection,
              orderField(value),
              collection.properties.direction,
            ),
          )
        }
        value={collection.properties.order_by}
      />
      <Input.Wrapper label="Direction">
        <SegmentedControl
          aria-label="Diagram sorting direction"
          data={directions}
          onChange={(value) =>
            onFollow(
              orderingTarget(
                collection,
                collection.properties.order_by,
                sortDirection(value),
              ),
            )
          }
          value={collection.properties.direction}
        />
      </Input.Wrapper>
    </>
  );
}
