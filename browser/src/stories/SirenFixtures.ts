import {
  Action,
  EmbeddedEntity,
  EmbeddedLink,
  Entity,
  Field,
  Link,
  type SubEntity,
} from "@siren-js/client";

export class SirenFixtures {
  link(href: string, rel: string[], title: string): Link {
    return Object.assign(new Link(), {
      class: [],
      href,
      rel,
      title,
    });
  }

  embeddedLink(href: string, rel: string[], title: string): EmbeddedLink {
    return Object.assign(new EmbeddedLink(), {
      class: [],
      href,
      rel,
      title,
    });
  }

  entity<T extends object>(
    classes: string[],
    title: string,
    properties: T,
    links: Link[],
    entities: SubEntity[],
    actions: Action[],
  ): Entity<T> {
    return Object.assign(new Entity<T>(), {
      actions,
      class: classes,
      entities,
      links,
      properties,
      title,
    });
  }

  embeddedEntity<T extends object>(
    classes: string[],
    rel: string[],
    title: string,
    properties: T,
    links: Link[],
  ): EmbeddedEntity<T> {
    return Object.assign(new EmbeddedEntity<T>(), {
      actions: [],
      class: classes,
      entities: [],
      links,
      properties,
      rel,
      title,
    });
  }

  action(
    name: string,
    title: string,
    href: string,
    method: string,
    fields: Field[],
  ): Action {
    return Object.assign(new Action(), {
      class: [],
      fields,
      href,
      method,
      name,
      title,
      type: "application/json",
    });
  }

  field(name: string, title: string, type: string): Field {
    return Object.assign(new Field(), {
      class: [],
      name,
      title,
      type,
    });
  }
}

export const sirenFixtures = new SirenFixtures();
