import type { Entity } from "@siren-js/client";
import type { ComponentType } from "react";
import type { SirenEntityProps } from "./SirenEntity";

export type SirenEntityRenderer = ComponentType<SirenEntityProps>;
export type SirenEntityRendererMatch = (entity: Entity) => boolean;

type ConditionalRenderer = {
  id: string;
  matches: SirenEntityRendererMatch;
  renderer: SirenEntityRenderer;
};

export class SirenEntityRendererRegistry {
  private readonly conditionalRenderers: ConditionalRenderer[] = [];
  private readonly renderers = new Map<string, SirenEntityRenderer>();

  register(className: string, renderer: SirenEntityRenderer): () => void {
    if (this.renderers.has(className))
      throw new Error(`A renderer is already registered for ${className}.`);
    this.renderers.set(className, renderer);
    return () => this.renderers.delete(className);
  }

  registerWhen(
    id: string,
    matches: SirenEntityRendererMatch,
    renderer: SirenEntityRenderer,
  ): () => void {
    if (this.conditionalRenderers.some((candidate) => candidate.id === id))
      throw new Error(
        `A conditional renderer is already registered for ${id}.`,
      );
    const registration = { id, matches, renderer };
    this.conditionalRenderers.push(registration);
    return () => {
      const index = this.conditionalRenderers.indexOf(registration);
      if (index >= 0) this.conditionalRenderers.splice(index, 1);
    };
  }

  resolve(entity: Entity): SirenEntityRenderer | undefined {
    const conditional = this.conditionalRenderers.find(({ matches }) =>
      matches(entity),
    );
    if (conditional) return conditional.renderer;
    for (const className of entity.class) {
      const renderer = this.renderers.get(className);
      if (renderer) return renderer;
    }
    return undefined;
  }
}
