import {
  EmbeddedLink,
  type Entity,
  type SubEntity,
  type Target,
} from "@siren-js/client";

export type Language = {
  id: string;
  name: string;
  aliases: string[];
  extensions: string[];
};
export type LanguageTarget =
  { kind: "available"; target: Target } | { kind: "unavailable" };

export class LanguageContract {
  read(entity: Entity | SubEntity): Language {
    if (entity instanceof EmbeddedLink)
      throw new Error(
        "Language metadata is missing. Reload to retrieve the complete resource.",
      );
    const raw: unknown = entity.properties;
    if (typeof raw !== "object" || raw === null || Array.isArray(raw))
      throw new Error(
        "Language metadata is missing. Reload to retrieve the complete resource.",
      );
    const data: Record<string, unknown> = Object.fromEntries(
      Object.entries(raw),
    );
    return {
      id: this.text(data.id),
      name: this.text(data.name),
      aliases: this.texts(data.aliases),
      extensions: this.texts(data.source_extensions),
    };
  }

  private text(value: unknown): string {
    if (typeof value !== "string" || !value.trim())
      throw new Error(
        "Language metadata contains a missing or invalid text field. Reload to try again.",
      );
    return value;
  }

  private texts(value: unknown): string[] {
    if (!Array.isArray(value))
      throw new Error(
        "Language metadata contains a missing or invalid list. Reload to try again.",
      );
    return value.map((item: unknown) => this.text(item));
  }

  target(entity: Entity | SubEntity): LanguageTarget {
    if (entity instanceof EmbeddedLink)
      return { kind: "available", target: entity };
    const link = entity.links.find(
      (candidate) =>
        candidate.rel.includes("self") || candidate.rel.includes("item"),
    );
    if (link) return { kind: "available", target: link };
    const action = entity.actions.find(
      (candidate) =>
        candidate.method === "GET" &&
        (candidate.name === "get_language" ||
          candidate.name === "find_languages"),
    );
    return action
      ? { kind: "available", target: action }
      : { kind: "unavailable" };
  }

  href(target: Target): string {
    return (typeof target === "string" ? target : target.href).toString();
  }
}
