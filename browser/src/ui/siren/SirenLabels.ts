import type { Entity, Link, SubEntity } from "@siren-js/client";

const GENERIC_CLASSES = new Set([
  "api",
  "collection",
  "entity",
  "entry-point",
  "item",
  "resource",
]);
const GENERIC_TITLES = new Set([
  "array",
  "entity",
  "item",
  "object",
  "resource",
  "response",
]);

function text(value: unknown): string | undefined {
  if (typeof value !== "string" && typeof value !== "number") return undefined;
  const result = String(value).trim();
  return result || undefined;
}

function title(value: unknown): string | undefined {
  const result = text(value);
  return result &&
    !GENERIC_TITLES.has(result.toLowerCase()) &&
    !/summary$/i.test(result)
    ? result
    : undefined;
}

function humanize(value: string): string {
  let decoded = value;
  try {
    decoded = decodeURIComponent(value);
  } catch {
    decoded = value;
  }
  const words = decoded
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .trim();
  return words
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function pluralize(value: string): string {
  if (/[^aeiou]y$/i.test(value)) return `${value.slice(0, -1)}ies`;
  if (/(s|x|z|ch|sh)$/i.test(value)) return `${value}es`;
  return value.endsWith("s") ? value : `${value}s`;
}

function resourceClass(classes: string[]): string | undefined {
  const className = [...classes]
    .reverse()
    .find((candidate) => !GENERIC_CLASSES.has(candidate.toLowerCase()));
  return className ? humanize(className) : undefined;
}

function linkPath(link: { href: string }): string | undefined {
  try {
    const path = new URL(link.href.toString(), window.location.origin).pathname;
    const segment = path.split("/").filter(Boolean).at(-1);
    return segment ? humanize(segment) : undefined;
  } catch {
    return undefined;
  }
}

function selfLink(value: object): Link | undefined {
  const links = (value as { links?: unknown }).links;
  return Array.isArray(links)
    ? (links as Link[]).find((link) => link.rel.includes("self"))
    : undefined;
}

function properties(item: object): Record<string, unknown> {
  return "properties" in item && typeof item.properties === "object"
    ? (item.properties as Record<string, unknown>)
    : {};
}

function identifyingProperty(item: object): string | undefined {
  const entries = Object.entries(properties(item));
  const display = entries.find(
    ([name, value]) => /^(title|name|label)$/i.test(name) && text(value),
  );
  if (display) return text(display[1]);
  const identifier = entries.find(
    ([name, value]) =>
      /(^id$|(^|[_-])(id|key|code|slug)$)/i.test(name) && text(value),
  );
  return identifier ? text(identifier[1]) : undefined;
}

export function collectionLabel(entity: Entity): string {
  const projected = title(entity.title);
  if (projected)
    return projected.includes(" ") ? projected : pluralize(humanize(projected));
  const className = resourceClass(entity.class);
  if (className) return pluralize(className);
  const link = selfLink(entity);
  return (link && linkPath(link)) || "Resources";
}

export function entityLabel(entity: Entity): string {
  return (
    title(entity.title) ??
    identifyingProperty(entity) ??
    resourceClass(entity.class) ??
    (selfLink(entity) && linkPath(selfLink(entity)!)) ??
    "Resource"
  );
}

export function itemTitle(item: SubEntity): string | undefined {
  return title(item.title);
}

export function collectionItemLabel(
  item: SubEntity,
  index: number,
  ambiguousTitle: boolean,
): string {
  const itemProperties = properties(item);
  if (itemProperties.title && itemProperties.id)
    return `${itemProperties.title} (${itemProperties.id})`;
  const projected = itemTitle(item);
  if (projected && !ambiguousTitle) return projected;
  const identity = identifyingProperty(item);
  if (identity)
    return projected && projected !== identity
      ? `${projected} — ${identity}`
      : identity;
  const directHref = (item as { href?: unknown }).href;
  const link: { href: string } | undefined =
    typeof directHref === "string" ? { href: directHref } : selfLink(item);
  const path = link && linkPath(link);
  if (path) return projected ? `${projected} — ${path}` : path;
  const className = resourceClass(item.class) ?? "Resource";
  return `${className} ${index + 1}`;
}

export function linkLabel(link: Link): string {
  const projected = title(link.title);
  if (projected)
    return link.rel.includes("collection") && !projected.includes(" ")
      ? pluralize(humanize(projected))
      : projected;
  return (
    linkPath(link) ??
    link.rel
      .filter((relation) => relation !== "self")
      .map(humanize)
      .find(Boolean) ??
    "Resource"
  );
}
