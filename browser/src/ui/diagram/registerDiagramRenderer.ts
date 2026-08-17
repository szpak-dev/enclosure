import { sirenRegistry } from "../siren/SirenRegistry";
import { DiagramEntity } from "./DiagramEntity";

let registered = false;

export function registerDiagramRenderer(): void {
  if (registered) return;
  sirenRegistry.entities.register("diagram", DiagramEntity);
  registered = true;
}
