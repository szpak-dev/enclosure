import type { Entity, Link } from "@siren-js/client";
import { expect, it } from "vitest";
import {
  isActiveNavigationGroup,
  navigationGroups,
  ownsNavigationTarget,
  relatedResources,
} from "../SirenNavigationModel";

function link(href: string, rel: string[], title: string): Link {
  return { href, rel, title } as Link;
}

it("groups root collections by their application path", () => {
  expect(
    navigationGroups("/siren/", [
      link("/siren/records", ["collection"], "Record"),
      link("/siren/records/tags", ["collection"], "Tag"),
      link("/siren/projects", ["collection"], "Project"),
    ]),
  ).toEqual([
    {
      id: "records",
      label: "Records",
      resources: [
        { id: "/siren/records", label: "Records", target: "/siren/records" },
        {
          id: "/siren/records/tags",
          label: "Tags",
          target: "/siren/records/tags",
        },
      ],
    },
    {
      id: "projects",
      label: "Projects",
      resources: [
        { id: "/siren/projects", label: "Projects", target: "/siren/projects" },
      ],
    },
  ]);
});

it("keeps only advertised related links for entity subresources", () => {
  const entity = {
    actions: [],
    class: ["project"],
    entities: [],
    links: [
      link("/siren/projects/project-1", ["self"], "Project"),
      link(
        "/siren/projects/project-1/architecture-configuration",
        ["related"],
        "Architecture configuration",
      ),
      link("/siren/projects/project-1/insights", ["command"], "Insights"),
    ],
    properties: {},
    title: "Project",
  } as unknown as Entity;

  expect(relatedResources(entity)).toEqual([
    {
      id: "/siren/projects/project-1/architecture-configuration",
      label: "Architecture configuration",
      target: "/siren/projects/project-1/architecture-configuration",
    },
  ]);
});

it("keeps the owning application active for nested resources", () => {
  const [records, projects] = navigationGroups("/siren/", [
    link("/siren/records", ["collection"], "Record"),
    link("/siren/projects", ["collection"], "Project"),
  ]);

  expect(isActiveNavigationGroup(records, "/siren/projects/project-1")).toBe(
    false,
  );
  expect(isActiveNavigationGroup(projects, "/siren/projects")).toBe(false);
  expect(isActiveNavigationGroup(projects, "/siren/projects/project-1")).toBe(
    true,
  );
  expect(ownsNavigationTarget(projects, "/siren/projects")).toBe(true);
  expect(ownsNavigationTarget(projects, "/siren/projects/project-1")).toBe(
    true,
  );
});
