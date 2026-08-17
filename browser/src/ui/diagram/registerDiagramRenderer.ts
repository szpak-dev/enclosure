import { sirenRegistry } from "../siren/SirenRegistry";
import { DiagramEntity } from "./DiagramEntity";
import { DiagramSetEntity } from "./DiagramSetEntity";

let registered = false;

export function registerDiagramRenderer(): void {
  if (registered) return;
  sirenRegistry.entities.register("diagram", DiagramEntity);
  sirenRegistry.entities.register("diagram-set", DiagramSetEntity);
  registered = true;
}
