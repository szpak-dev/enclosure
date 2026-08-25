import type { Entity, Link, Target } from "@siren-js/client";
import { linkLabel } from "./SirenLabels";

export type NavigationGroup = Readonly<{
  id: string;
  label: string;
  resources: readonly NavigationResource[];
}>;

export type NavigationResource = Readonly<{
  id: string;
  label: string;
  target: string;
}>;

export type NavigationItem = Readonly<{
  id: string;
  label: string;
  target: string;
}>;

function targetId(target: Target): string {
  return (typeof target === "string" ? target : target.href).toString();
}

function pathSegments(target: Target): string[] {
  return new URL(targetId(target), window.location.origin).pathname
    .split("/")
    .filter(Boolean);
}

function targetPath(target: Target): string {
  return new URL(targetId(target), window.location.origin).pathname;
}

function applicationId(rootTarget: Target, target: Target): string {
  const rootSegments = pathSegments(rootTarget);
  const targetSegments = pathSegments(target);
  const rootPrefix = rootSegments.every(
    (segment, index) => targetSegments[index] === segment,
  );
  return (
    (rootPrefix ? targetSegments[rootSegments.length] : targetSegments[0]) ??
    targetId(target)
  );
}

function applicationLabel(id: string): string {
  return id
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .replace(/^./, (character) => character.toUpperCase());
}

export function navigationGroups(
  rootTarget: Target,
  links: readonly Link[],
): NavigationGroup[] {
  const groups = new Map<string, NavigationGroup>();
  links.forEach((link) => {
    if (!link.rel.includes("collection") || link.rel.includes("self")) return;
    const id = applicationId(rootTarget, link);
    const group = groups.get(id) ?? {
      id,
      label: applicationLabel(id),
      resources: [],
    };
    groups.set(id, {
      ...group,
      resources: [
        ...group.resources,
        { id: targetId(link), label: linkLabel(link), target: targetId(link) },
      ],
    });
  });
  return [...groups.values()];
}

export function isActiveNavigationGroup(
  group: NavigationGroup,
  activeTarget: Target,
): boolean {
  return (
    ownsNavigationTarget(group, activeTarget) &&
    !group.resources.some(
      (resource) => targetPath(resource.target) === targetPath(activeTarget),
    )
  );
}

export function ownsNavigationTarget(
  group: NavigationGroup,
  target: Target,
): boolean {
  const activePath = targetPath(target);
  return group.resources.some((resource) => {
    const resourcePath = targetPath(resource.target);
    return (
      activePath === resourcePath || activePath.startsWith(`${resourcePath}/`)
    );
  });
}

export function navigableResources(entity: Entity): NavigationItem[] {
  return entity.links.reduce<NavigationItem[]>((resources, link) => {
    if (!link.rel.includes("related") && !link.rel.includes("collection"))
      return resources;
    resources.push({
      id: targetId(link),
      label: linkLabel(link),
      target: targetId(link),
    });
    return resources;
  }, []);
}
