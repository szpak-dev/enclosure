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

const failingDiagramIds = vi.hoisted(() => new Set<string>());

vi.mock("../DiagramRenderer", () => ({
  DiagramRenderer: ({ diagramId }: { diagramId: string }) => {
    if (failingDiagramIds.has(diagramId)) {
      throw new Error(`Rendering failed for ${diagramId}`);
    }
    return <div aria-label={`Rendered ${diagramId}`} role="img" />;
  },
}));

const intersectionObservers: IntersectionObserverMock[] = [];

class IntersectionObserverMock implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "200px";
  readonly thresholds = [0];
  private target!: Element;

  constructor(private readonly callback: IntersectionObserverCallback) {
    intersectionObservers.push(this);
  }

  disconnect(): void {}

  intersect(): void {
    const bounds = this.target.getBoundingClientRect();
    this.callback(
      [
        {
          boundingClientRect: bounds,
          intersectionRatio: 1,
          intersectionRect: bounds,
          isIntersecting: true,
          rootBounds: null,
          target: this.target,
          time: 0,
        },
      ],
      this,
    );
  }

  observe(target: Element): void {
    this.target = target;
  }

  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }

  unobserve(): void {}
}

globalThis.IntersectionObserver = IntersectionObserverMock;

afterEach(() => {
  cleanup();
  failingDiagramIds.clear();
  intersectionObservers.length = 0;
});

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

function fullDiagram(index: number) {
  return {
    ...diagram(index),
    properties: {
      ...diagram(index).properties,
      snapshot: {},
      source: "flowchart LR\nA-->B",
    },
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
        onRefresh={vi.fn()}
        onSubmit={vi.fn()}
        root={diagramSet}
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

it("loads and renders only a diagram whose card becomes visible", async () => {
  const onLoad = vi
    .fn()
    .mockResolvedValueOnce(collection())
    .mockResolvedValueOnce(fullDiagram(1));
  renderGallery(onLoad);

  expect(await screen.findByText("Showing 27 of 27 diagrams")).toBeVisible();
  expect(onLoad).toHaveBeenCalledOnce();
  expect(intersectionObservers).toHaveLength(27);

  intersectionObservers[0].intersect();

  expect(
    await screen.findByRole("img", { name: "Rendered diagram-1" }),
  ).toBeVisible();
  expect(onLoad).toHaveBeenCalledTimes(2);
  expect(onLoad).toHaveBeenLastCalledWith(
    expect.objectContaining({ href: "/siren/diagrams/diagram-1" }),
  );
});

it("contains a rendering failure within its diagram card", async () => {
  const onLoad = vi
    .fn()
    .mockResolvedValueOnce(collection())
    .mockResolvedValueOnce(fullDiagram(1))
    .mockResolvedValueOnce(fullDiagram(2));
  failingDiagramIds.add("diagram-1");
  renderGallery(onLoad);

  await screen.findByText("Showing 27 of 27 diagrams");
  intersectionObservers[0].intersect();
  intersectionObservers[1].intersect();

  expect(
    await screen.findByText("Rendering failed for diagram-1"),
  ).toBeVisible();
  expect(screen.getByRole("img", { name: "Rendered diagram-2" })).toBeVisible();
  expect(screen.getByText("Showing 27 of 27 diagrams")).toBeVisible();
  expect(screen.getAllByRole("link", { name: "Open diagram" })).toHaveLength(
    27,
  );
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
        onRefresh={vi.fn()}
        onSubmit={vi.fn()}
        root={diagramSet}
      />
    </MantineProvider>,
  );

  expect(screen.getByRole("alert")).toHaveTextContent(
    "does not advertise a collection relationship",
  );
});
