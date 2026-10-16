import {
  EmbeddedLink,
  type Action,
  type Entity,
  type Link,
  type SubEntity,
  type Target,
} from "@siren-js/client";

export type PresentedValue =
  { kind: "present"; value: unknown } | { kind: "absent" };

export type PresentedTarget =
  { kind: "present"; target: Target } | { kind: "absent" };

export class ProjectPresentation {
  value(properties: object, name: string): PresentedValue {
    for (const [key, value] of Object.entries(properties)) {
      if (key === name) return { kind: "present", value };
    }
    return { kind: "absent" };
  }

  text(properties: object, name: string): string {
    const presented = this.value(properties, name);
    if (presented.kind === "absent") return "Not reported";
    if (typeof presented.value === "string")
      return presented.value.trim() ? presented.value : "Not reported";
    if (typeof presented.value === "number") return String(presented.value);
    if (typeof presented.value === "boolean")
      return presented.value ? "Yes" : "No";
    return "Not reported";
  }

  inputText(properties: object, name: string): string {
    const presented = this.value(properties, name);
    return presented.kind === "present" && typeof presented.value === "string"
      ? presented.value
      : "";
  }

  itemProperties(item: SubEntity): object {
    return item instanceof EmbeddedLink ? {} : item.properties;
  }

  itemTarget(item: SubEntity): PresentedTarget {
    if (item instanceof EmbeddedLink) return { kind: "present", target: item };
    const itemLink = item.links.find((link) => link.rel.includes("item"));
    if (itemLink) return { kind: "present", target: itemLink };
    const selfLink = item.links.find((link) => link.rel.includes("self"));
    return selfLink
      ? { kind: "present", target: selfLink }
      : { kind: "absent" };
  }

  recordTarget(item: SubEntity, recordId: string): PresentedTarget {
    if (item instanceof EmbeddedLink) return { kind: "absent" };
    const link = item.links.find(
      (candidate) =>
        candidate.rel.includes("item") && candidate.href.includes(recordId),
    );
    return link ? { kind: "present", target: link } : { kind: "absent" };
  }

  action(entity: Entity, name: string): Action | { name: "absent" } {
    const action = entity.actions.find((candidate) => candidate.name === name);
    return action ? action : { name: "absent" };
  }

  label(value: string): string {
    const labels: Record<string, string> = {
      ArchitectureContractPublication: "Architecture contract publications",
      GuidanceRelationship: "Guidance relationships",
      GuidanceScope: "Guidance scopes",
      ProjectArchitectureConfiguration: "Architecture configurations",
      WorkspaceBinding: "Workspaces",
      architecture_root: "Architecture root",
      boundaries_total_characters: "Boundaries size",
      contract_id: "Contract ID",
      id: "ID",
      language_id: "Language",
      language_version: "Language version",
      package_manager_id: "Package manager",
      project_id: "Project ID",
      record_id: "Record ID",
      revision: "Revision",
      scaffolding_id: "Scaffolding ID",
      shape_total_characters: "Shape size",
      source_record_id: "Source record ID",
      target_record_id: "Target record ID",
      update_policy: "Update policy",
    };
    const known = labels[value];
    if (known) return known;
    return value
      .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
      .replace(/_/g, " ")
      .replace(/^./, (character) => character.toUpperCase());
  }

  linkLabel(link: Link): string {
    return link.title ? this.label(link.title) : "Related resource";
  }

  title(entity: Entity, fallback: string): string {
    const title = this.text(entity.properties, "title");
    return title === "Not reported" ? fallback : title;
  }
}

export const projectPresentation = new ProjectPresentation();
