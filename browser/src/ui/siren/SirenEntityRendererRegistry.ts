import type { ComponentType } from "react";
import type { SirenEntityProps } from "./SirenEntity";

export type SirenEntityRenderer = ComponentType<SirenEntityProps>;

export class SirenEntityRendererRegistry {
  private readonly renderers = new Map<string, SirenEntityRenderer>();

  register(className: string, renderer: SirenEntityRenderer): () => void {
    if (this.renderers.has(className))
      throw new Error(`A renderer is already registered for ${className}.`);
    this.renderers.set(className, renderer);
    return () => this.renderers.delete(className);
  }

  resolve(classNames: readonly string[]): SirenEntityRenderer | undefined {
    for (const className of classNames) {
      const renderer = this.renderers.get(className);
      if (renderer) return renderer;
    }
    return undefined;
  }
}
