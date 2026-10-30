import type { Entity } from "@siren-js/client";
import { sirenRegistry } from "../siren/SirenRegistry";
import { RecordCollection } from "./RecordCollection";
import { RecordDetail } from "./RecordDetail";
import {
  RecordClassificationCollection,
  RecordCategoryDetail,
  RecordTagDetail,
} from "./RecordClassification";
import { RecordDocument, RecordResourceManifests } from "./RecordDocuments";

class RecordRendererRegistration {
  private registered = false;
  register(): void {
    if (this.registered) return;
    sirenRegistry.collections.register("record", RecordCollection);
    sirenRegistry.collections.register(
      "category",
      RecordClassificationCollection,
    );
    sirenRegistry.collections.register("tag", RecordClassificationCollection);
    sirenRegistry.collections.register(
      "resource-manifest",
      RecordResourceManifests,
    );
    sirenRegistry.collections.registerWhen(
      "record-search",
      (entity: Entity) =>
        entity.title === "RecordSummary" ||
        entity.class.includes("record-summary"),
      RecordCollection,
    );
    sirenRegistry.entities.register("record", RecordDetail);
    sirenRegistry.entities.register("category", RecordCategoryDetail);
    sirenRegistry.entities.register("tag", RecordTagDetail);
    sirenRegistry.entities.registerWhen(
      "record-document",
      (entity: Entity) =>
        entity.class.includes("command-result") &&
        Object.hasOwn(entity.properties, "content") &&
        Object.hasOwn(entity.properties, "revision") &&
        (Object.hasOwn(entity.properties, "record_id") ||
          Object.hasOwn(entity.properties, "category_id")),
      RecordDocument,
    );
    for (const name of [
      "record-json-content",
      "record-resource-content",
      "record-category-content-schema",
    ])
      sirenRegistry.entities.register(name, RecordDocument);
    this.registered = true;
  }
}

const registration = new RecordRendererRegistration();
export function registerRecordRenderers(): void {
  registration.register();
}
