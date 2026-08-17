import { Alert } from "@mantine/core";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { DiagramGallery } from "./DiagramGallery";

export function DiagramSetEntity(props: SirenEntityProps) {
  const collectionTarget = props.entity.links.find((link) =>
    link.rel.includes("collection"),
  );

  if (!collectionTarget) {
    return (
      <Alert color="red" role="alert" title="Diagram collection unavailable">
        This diagram set does not advertise a collection relationship.
      </Alert>
    );
  }

  return <DiagramGallery {...props} collectionTarget={collectionTarget} />;
}
