import { MantineProvider } from "@mantine/core";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { Entity, Target } from "@siren-js/client";
import { afterEach, expect, it, vi } from "vitest";
import { DiagramSetEntity } from "../DiagramSetEntity";

afterEach(cleanup);

const collectionTarget = {
  class: [],
  href: "/siren/diagram-sets/set-one/diagrams",
  rel: ["collection"],
  title: "Diagrams",
} as unknown as Target;

const diagramSet = {
  actions: [],
  class: ["diagram-set"],
  entities: [],
  links: [
    { href: "/siren/diagram-sets/set-one", rel: ["self"] },
    collectionTarget,
  ],
  properties: {
    description: "Twenty-seven diagram kinds.",
    id: "set-one",
    title: "Diagram proof",
  },
  title: "Diagram set",
} as unknown as Entity;

function diagram(index: number) {
  const id = `diagram-${index}`;
  return {
    actions: [],
    class: ["diagram"],
    entities: [],
    links: [{ href: `/siren/diagrams/${id}`, rel: ["self"] }],
    properties: {
      id,
      kind: index % 2 ? "flowchart" : "sequence",
      revision: 1,
      title: index === 1 ? "Exact target" : `Diagram ${index}`,
    },
    rel: ["item"],
    title: "Diagram",
  };
}

function collection() {
  return {
    actions: [],
    class: ["collection", "diagram"],
    entities: Array.from({ length: 27 }, (_, index) => diagram(index + 1)),
    links: [collectionTarget],
    properties: {},
    title: "Diagrams",
  } as unknown as Entity;
}

function renderGallery(onLoad = vi.fn().mockResolvedValue(collection())) {
  const onFollow = vi.fn();
  render(
    <MantineProvider>
      <DiagramSetEntity
        entity={diagramSet}
        onFollow={onFollow}
        onLoad={onLoad}
        onSubmit={vi.fn()}
      />
    </MantineProvider>,
  );
  return { onFollow, onLoad };
}

it("discovers and displays all 27 diagram summaries", async () => {
  const { onLoad } = renderGallery();

  expect(await screen.findByText("Showing 27 of 27 diagrams")).toBeVisible();
  expect(screen.getAllByRole("article")).toHaveLength(28);
  expect(onLoad).toHaveBeenCalledOnce();
  expect(onLoad).toHaveBeenCalledWith(collectionTarget);
});

it("filters diagrams by title and kind", async () => {
  renderGallery();
  await screen.findByText("Showing 27 of 27 diagrams");

  fireEvent.change(screen.getByRole("textbox", { name: "Search diagrams" }), {
    target: { value: "Exact target" },
  });
  expect(screen.getByText("Showing 1 of 27 diagrams")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Exact target" })).toBeVisible();

  fireEvent.change(screen.getByRole("textbox", { name: "Search diagrams" }), {
    target: { value: "" },
  });
  fireEvent.change(screen.getByRole("combobox", { name: "Diagram kind" }), {
    target: { value: "sequence" },
  });
  expect(screen.getByText("Showing 13 of 27 diagrams")).toBeVisible();
});

it("switches layout and follows the selected diagram self relationship", async () => {
  const { onFollow } = renderGallery();
  await screen.findByText("Showing 27 of 27 diagrams");

  fireEvent.click(screen.getByText("List"));
  expect(
    screen.getByRole("region", { name: "list diagram gallery" }),
  ).toBeVisible();

  fireEvent.click(screen.getAllByRole("link", { name: "Open diagram" })[0]);
  expect(onFollow).toHaveBeenCalledWith(
    expect.objectContaining({ href: "/siren/diagrams/diagram-1" }),
  );
});

it("shows collection failures and retries through the same Siren target", async () => {
  const onLoad = vi
    .fn()
    .mockRejectedValueOnce(new Error("Collection unavailable"))
    .mockResolvedValueOnce(collection());
  renderGallery(onLoad);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Collection unavailable",
  );
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));

  expect(await screen.findByText("Showing 27 of 27 diagrams")).toBeVisible();
  await waitFor(() => expect(onLoad).toHaveBeenCalledTimes(2));
  expect(onLoad).toHaveBeenNthCalledWith(1, collectionTarget);
  expect(onLoad).toHaveBeenNthCalledWith(2, collectionTarget);
});

it("reports a missing collection relationship", () => {
  render(
    <MantineProvider>
      <DiagramSetEntity
        entity={{ ...diagramSet, links: [] } as unknown as Entity}
        onFollow={vi.fn()}
        onLoad={vi.fn()}
        onSubmit={vi.fn()}
      />
    </MantineProvider>,
  );

  expect(screen.getByRole("alert")).toHaveTextContent(
    "does not advertise a collection relationship",
  );
});
