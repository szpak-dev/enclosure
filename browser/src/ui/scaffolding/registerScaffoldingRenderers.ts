import { sirenRegistry } from "../siren/SirenRegistry";
import {
  isScaffoldingSearchResult,
  ScaffoldingCollection,
} from "./ScaffoldingCollection";
import { ScaffoldingEntity } from "./ScaffoldingEntity";
import { TemplateManifestCollection } from "./TemplateManifestCollection";

let registered = false;

export function registerScaffoldingRenderers(): void {
  if (registered) return;
  sirenRegistry.collections.register("scaffolding", ScaffoldingCollection);
  sirenRegistry.collections.register(
    "template-manifest",
    TemplateManifestCollection,
  );
  sirenRegistry.collections.registerWhen(
    "scaffolding-search-results",
    isScaffoldingSearchResult,
    ScaffoldingCollection,
  );
  sirenRegistry.entities.register("scaffolding", ScaffoldingEntity);
  registered = true;
}
