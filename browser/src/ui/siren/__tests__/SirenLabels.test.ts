import { EmbeddedEntity, EmbeddedLink, Entity, Link } from "@siren-js/client";
import { describe, expect, it } from "vitest";
import {
  collectionItemLabel,
  collectionLabel,
  entityLabel,
  linkLabel,
} from "../SirenLabels";

function link(href: string, title?: string): Link {
  return Object.assign(new Link(), {
    class: [],
    href,
    rel: ["self"],
    title,
  });
}

function item(
  properties: Record<string, unknown>,
  options: { href?: string; title?: string } = {},
): EmbeddedEntity {
  return Object.assign(new EmbeddedEntity(), {
    actions: [],
    class: ["record-category"],
    entities: [],
    links: options.href ? [link(options.href)] : [],
    properties,
    rel: ["item"],
    title: options.title,
  });
}

function collection(title?: string): Entity {
  return Object.assign(new Entity(), {
    actions: [],
    class: ["collection", "record-category"],
    entities: [],
    links: [link("/api/record-categories")],
    properties: {},
    title,
  });
}

describe("Siren labels", () => {
  it("shows titled resources with their identifiers", () => {
    expect(
      collectionItemLabel(
        item(
          { id: "project-42", title: "Enclosure" },
          { title: "Project Reference" },
        ),
        0,
        true,
      ),
    ).toBe("Enclosure (project-42)");
  });

  it("keeps meaningful projected collection titles", () => {
    expect(collectionLabel(collection("Available categories"))).toBe(
      "Available categories",
    );
  });

  it("replaces framework collection titles with a domain class label", () => {
    expect(collectionLabel(collection("Response"))).toBe("Record Categories");
    expect(collectionLabel(collection("RecordCategorySummary"))).toBe(
      "Record Categories",
    );
    expect(collectionLabel(collection("RecordCategory"))).toBe(
      "Record Categories",
    );
  });

  it("distinguishes repeated item titles with identifying properties", () => {
    expect(
      collectionItemLabel(
        item({ name: "Architecture" }, { title: "Record Category" }),
        0,
        true,
      ),
    ).toBe("Record Category — Architecture");
    expect(
      collectionItemLabel(
        item({ name: "Testing" }, { title: "Record Category" }),
        1,
        true,
      ),
    ).toBe("Record Category — Testing");
  });

  it("falls back through identifiers, self paths, and stable row numbers", () => {
    expect(
      collectionItemLabel(item({ project_id: "project-42" }), 0, false),
    ).toBe("project-42");
    expect(
      collectionItemLabel(
        Object.assign(new EmbeddedLink(), {
          class: [],
          href: "/api/records/42",
          rel: ["item"],
          title: "Response",
        }),
        1,
        false,
      ),
    ).toBe("42");
    expect(collectionItemLabel(item({}), 2, false)).toBe("Record Category 3");
  });

  it("uses the same defensive fallbacks for entities and links", () => {
    const exampleEntity = Object.assign(new Entity(), {
      actions: [],
      class: ["record"],
      entities: [],
      links: [],
      properties: { label: "Example record" },
      title: "Resource",
    });
    const exampleLink = Object.assign(new Link(), {
      class: [],
      href: "/api/example-resources",
      rel: ["collection"],
      title: "Response",
    });

    expect(entityLabel(exampleEntity)).toBe("Example record");
    expect(linkLabel(exampleLink)).toBe("Example Resources");
  });

  it("pluralizes projected resource names used for collection links", () => {
    const categoryLink = Object.assign(new Link(), {
      class: [],
      href: "/api/records/categories",
      rel: ["collection"],
      title: "Category",
    });
    const summaryLink = Object.assign(new Link(), {
      class: [],
      href: "/api/scaffoldings",
      rel: ["collection"],
      title: "ScaffoldingSummary",
    });

    expect(linkLabel(categoryLink)).toBe("Categories");
    expect(linkLabel(summaryLink)).toBe("Scaffoldings");
  });
});
