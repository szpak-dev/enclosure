import { MantineProvider, Text } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import type { Entity } from "@siren-js/client";
import { type ReactElement } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { SirenEntity, type SirenEntityProps } from "../SirenEntity";
import { sirenRegistry } from "../SirenRegistry";

const unregister: Array<() => void> = [];

afterEach(() => {
  unregister.splice(0).forEach((remove) => remove());
});

function entity(classes: string[]): Entity {
  return {
    actions: [],
    class: classes,
    entities: [],
    links: [],
    properties: { title: "Generic resource" },
    title: "Generic resource",
  } as unknown as Entity;
}

function renderEntity(value: Entity): void {
  render(
    <MantineProvider>
      <SirenEntity entity={value} onFollow={vi.fn()} onSubmit={vi.fn()} />
    </MantineProvider>,
  );
}

it("renders an entity with the first registered resource renderer", () => {
  function SpecializedEntity({ entity }: SirenEntityProps): ReactElement {
    return <Text>Specialized {entity.title}</Text>;
  }
  unregister.push(
    sirenRegistry.entities.register("specialized", SpecializedEntity),
  );

  renderEntity(entity(["unknown", "specialized"]));

  expect(screen.getByText("Specialized Generic resource")).toBeVisible();
  expect(
    screen.queryByRole("heading", { name: "Generic resource" }),
  ).not.toBeInTheDocument();
});

it("falls back to the generic resource view for unknown classes", () => {
  renderEntity(entity(["unknown"]));

  expect(
    screen.getByRole("heading", { name: "Generic resource" }),
  ).toBeVisible();
});

it("rejects duplicate renderer registrations", () => {
  const Renderer = (): ReactElement => <Text>Specialized</Text>;
  unregister.push(sirenRegistry.entities.register("specialized", Renderer));

  expect(() =>
    sirenRegistry.entities.register("specialized", Renderer),
  ).toThrow("A renderer is already registered for specialized.");
});
