import { Collapse, NavLink, Stack } from "@mantine/core";
import type { Target } from "@siren-js/client";
import { useEffect, useState } from "react";
import {
  isActiveNavigationGroup,
  ownsNavigationTarget,
  type NavigationGroup,
} from "./SirenNavigationModel";

export type SirenNavigationProps = {
  activeTarget: Target;
  groups: readonly NavigationGroup[];
  onFollow: (target: Target) => void;
};

function href(target: Target): string {
  return (typeof target === "string" ? target : target.href).toString();
}

function sameTarget(left: Target, right: Target): boolean {
  return (
    new URL(href(left), window.location.origin).href ===
    new URL(href(right), window.location.origin).href
  );
}

export function SirenNavigation({
  activeTarget,
  groups,
  onFollow,
}: SirenNavigationProps) {
  const [expandedGroups, setExpandedGroups] = useState<ReadonlySet<string>>(
    new Set(),
  );

  useEffect(() => {
    const activeGroupIds = groups
      .filter((group) => ownsNavigationTarget(group, activeTarget))
      .map((group) => group.id);
    if (!activeGroupIds.length) return;
    setExpandedGroups((current) => new Set([...current, ...activeGroupIds]));
  }, [activeTarget, groups]);

  const toggle = (group: NavigationGroup) =>
    setExpandedGroups((current) => {
      const next = new Set(current);
      if (next.has(group.id)) next.delete(group.id);
      else next.add(group.id);
      return next;
    });

  return (
    <nav aria-label="Applications">
      <Stack gap={2}>
        {groups.map((group) => {
          const expanded = expandedGroups.has(group.id);
          return (
            <Stack gap={2} key={group.id}>
              <NavLink
                active={isActiveNavigationGroup(group, activeTarget)}
                component="button"
                label={group.label}
                onClick={() => toggle(group)}
                opened={expanded}
              />
              <Collapse expanded={expanded}>
                <Stack gap={2} pl="md">
                  {group.resources.map((resource) => (
                    <NavLink
                      active={sameTarget(activeTarget, resource.target)}
                      component="a"
                      href={`#${href(resource.target)}`}
                      key={resource.id}
                      label={resource.label}
                      onClick={(event) => {
                        event.preventDefault();
                        onFollow(resource.target);
                      }}
                    />
                  ))}
                </Stack>
              </Collapse>
            </Stack>
          );
        })}
      </Stack>
    </nav>
  );
}
