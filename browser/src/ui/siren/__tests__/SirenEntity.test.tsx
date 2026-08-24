import { MantineProvider, Text } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
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

function renderEntity(
  value: Entity,
  onLoad: SirenEntityProps["onLoad"] = vi.fn(),
): void {
  render(
    <MantineProvider>
      <SirenEntity
        entity={value}
        onFollow={vi.fn()}
        onLoad={onLoad}
        onRefresh={vi.fn()}
        onSubmit={vi.fn()}
        root={entity(["api", "entry-point"])}
      />
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

it("provides the resource loader to a specialized renderer", () => {
  const onLoad = vi.fn().mockResolvedValue(entity(["related"]));
  function SpecializedEntity({ onLoad }: SirenEntityProps): ReactElement {
    return (
      <button onClick={() => void onLoad("/related")}>Load related</button>
    );
  }
  unregister.push(
    sirenRegistry.entities.register("specialized", SpecializedEntity),
  );

  renderEntity(entity(["specialized"]), onLoad);
  fireEvent.click(screen.getByRole("button", { name: "Load related" }));

  expect(onLoad).toHaveBeenCalledOnce();
  expect(onLoad).toHaveBeenCalledWith("/related");
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
