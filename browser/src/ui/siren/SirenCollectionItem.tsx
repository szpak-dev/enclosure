import { EmbeddedLink, type SubEntity, type Target } from "@siren-js/client";
import { NavLink, Stack, Text } from "@mantine/core";
import type { ReactElement } from "react";
import { RelativeTime } from "../time/RelativeTime";
import { collectionItemPresentation } from "./SirenLabels";

export type SirenCollectionItemProps = {
  ambiguousTitle: boolean;
  index: number;
  item: SubEntity;
  onFollow: (target: Target) => void;
};

export function SirenCollectionItem({
  ambiguousTitle,
  index,
  item,
  onFollow,
}: SirenCollectionItemProps) {
  const target =
    item instanceof EmbeddedLink
      ? item
      : (item.links.find((link) => link.rel.includes("self")) ??
        item.links.find((link) => !link.rel.includes("self")));
  const presentation = collectionItemPresentation(item, index, ambiguousTitle);
  const description: ReactElement | string | undefined =
    presentation.kind === "title-and-description" ? (
      presentation.description
    ) : presentation.kind === "title-and-updated-at" ? (
      <RelativeTime prefix="Updated " timestamp={presentation.updatedAt} />
    ) : undefined;

  if (!target) {
    return (
      <Stack gap={0} py="xs">
        <Text>{presentation.title}</Text>
        {description ? (
          <Text c="dimmed" size="sm">
            {description}
          </Text>
        ) : null}
      </Stack>
    );
  }

  return (
    <NavLink
      component="a"
      href={`#${target.href}`}
      label={presentation.title}
      onClick={(event) => {
        event.preventDefault();
        onFollow(target);
      }}
      {...(description ? { description } : {})}
    />
  );
}
