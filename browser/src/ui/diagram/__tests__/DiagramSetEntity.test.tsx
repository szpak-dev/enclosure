import { MantineProvider } from "@mantine/core";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import type { Entity } from "@siren-js/client";
import { afterEach, expect, it, vi } from "vitest";
import { DiagramSetEntity } from "../DiagramSetEntity";

const collectionTarget = {
  class: [],
  href: "/siren/diagram-sets/example-set/diagrams",
  rel: ["collection"],
  title: "Diagrams",
};

const diagramSet = {
  actions: [],
  class: ["diagram-set"],
  entities: [],
  links: [
    { href: "/siren/diagram-sets/example-set", rel: ["self"] },
    collectionTarget,
  ],
  properties: {
    description: "Example diagrams.",
    id: "example-set",
    title: "Example diagram set",
  },
  title: "Diagram set",
} as unknown as Entity;

function summary(
  id: string,
  title: string,
  updatedAt: string,
  withSelf = true,
) {
  return {
    actions: [],
    class: ["diagram"],
    entities: [],
    links: withSelf
      ? [{ href: `/siren/diagrams/${id}`, rel: ["self"], title }]
      : [],
    properties: {
      id,
      kind: "flowchart-v2",
      revision: 1,
      title,
      updated_at: updatedAt,
    },
    rel: ["item"],
    title: "Diagram",
  };
}

function collection(
  entities = [
    summary(
      "example-diagram-one",
      "Example request flow",
      "2026-10-15T08:30:00Z",
    ),
    summary(
      "example-diagram-two",
      "Example command flow",
      "2026-10-14T16:20:00Z",
    ),
  ],
) {
  return {
    actions: [],
    class: ["collection", "diagram"],
    entities,
    links: [
      {
        href: "/siren/diagram-sets/example-set/diagrams?limit=50&order_by=updated_at&direction=desc",
        rel: ["self"],
        title: "Diagrams",
      },
      {
        href: "/siren/diagram-sets/example-set/diagrams?offset=50&limit=50&order_by=updated_at&direction=desc",
        rel: ["next"],
        title: "Next page",
      },
    ],
    properties: {
      direction: "desc",
      has_more: true,
      limit: 50,
      next_offset: 50,
      order_by: "updated_at",
    },
    title: "Diagrams",
  } as unknown as Entity;
}

function detail(id: string, title: string) {
  return {
    actions: [],
    class: ["diagram"],
    entities: [],
    links: [{ href: `/siren/diagrams/${id}`, rel: ["self"] }],
    properties: {
      id,
      kind: "flowchart-v2",
      revision: 1,
      snapshot: { version: 1 },
      source: "flowchart LR\nExampleA-->ExampleB",
      title,
      updated_at: "2026-10-15T08:30:00Z",
    },
    title: "Diagram",
  } as unknown as Entity;
}

function renderDiagramSet(onLoad = vi.fn().mockResolvedValue(collection())) {
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

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("rejects a diagram set without its advertised diagram collection", () => {
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

it("rejects a response that is not an ordered diagram collection", async () => {
  const onLoad = vi.fn().mockResolvedValue({
    ...collection(),
    class: ["collection", "record"],
  });
  renderDiagramSet(onLoad);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Diagram collection ordering is unavailable.",
  );
  expect(screen.queryByRole("list", { name: "Diagrams" })).toBeNull();
});

it("recovers from a collection failure through the advertised target", async () => {
  const onLoad = vi
    .fn()
    .mockRejectedValueOnce(new Error("Example collection unavailable"))
    .mockResolvedValueOnce(collection());
  renderDiagramSet(onLoad);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Example collection unavailable",
  );
  expect(screen.queryByRole("list", { name: "Diagrams" })).toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "Retry" }));

  expect(await screen.findByRole("list", { name: "Diagrams" })).toBeVisible();
  expect(onLoad).toHaveBeenNthCalledWith(1, collectionTarget);
  expect(onLoad).toHaveBeenNthCalledWith(2, collectionTarget);
});

it("contains a diagram without a self relationship in an explanatory row", async () => {
  renderDiagramSet(
    vi
      .fn()
      .mockResolvedValue(
        collection([
          summary(
            "example-diagram-missing-link",
            "Example incomplete diagram",
            "2026-10-15T08:30:00Z",
            false,
          ),
        ]),
      ),
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Diagram details and preview are unavailable",
  );
  expect(
    screen.queryByRole("button", {
      name: "Preview Example incomplete diagram",
    }),
  ).toBeNull();
});

it("presents diagrams as one-link list rows with type and exact update time", async () => {
  vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-10-15T08:40:00Z"));
  renderDiagramSet();

  const list = await screen.findByRole("list", { name: "Diagrams" });
  expect(within(list).getAllByRole("listitem")).toHaveLength(2);
  expect(
    within(list).getByRole("link", { name: /Example request flow/ }),
  ).toBeVisible();
  expect(within(list).getAllByText("flowchart-v2")).toHaveLength(2);
  expect(within(list).getByText("Updated 10 minutes ago")).toHaveAttribute(
    "title",
    "2026-10-15T08:30:00Z",
  );
  expect(
    within(list).getByRole("button", { name: "Preview Example request flow" }),
  ).toBeVisible();
  expect(within(list).queryAllByRole("img")).toHaveLength(0);
});

it("follows a diagram row and the collection continuation without duplicate links", async () => {
  const { onFollow } = renderDiagramSet();
  const list = await screen.findByRole("list", { name: "Diagrams" });

  fireEvent.click(
    within(list).getByRole("link", { name: /Example request flow/ }),
  );
  expect(onFollow).toHaveBeenCalledWith(
    expect.objectContaining({
      href: "/siren/diagrams/example-diagram-one",
    }),
  );

  fireEvent.click(screen.getByRole("link", { name: "Next page" }));
  expect(onFollow).toHaveBeenLastCalledWith(
    expect.objectContaining({
      href: "/siren/diagram-sets/example-set/diagrams?offset=50&limit=50&order_by=updated_at&direction=desc",
    }),
  );
  expect(within(list).getAllByRole("link")).toHaveLength(2);
});

it("follows caller-selected ordering from the first page", async () => {
  const { onFollow } = renderDiagramSet();
  await screen.findByRole("list", { name: "Diagrams" });

  fireEvent.click(screen.getByRole("combobox", { name: "Sort by" }));
  fireEvent.click(screen.getByRole("option", { hidden: true, name: "Title" }));
  expect(onFollow).toHaveBeenCalledWith(
    "/siren/diagram-sets/example-set/diagrams?limit=50&order_by=title&direction=desc&offset=0",
  );

  fireEvent.click(screen.getByText("Ascending"));
  expect(onFollow).toHaveBeenLastCalledWith(
    "/siren/diagram-sets/example-set/diagrams?limit=50&order_by=updated_at&direction=asc&offset=0",
  );
});

it("loads a row preview into the full-screen Mermaid viewer", async () => {
  if (!customElements.get("mermaid-embed")) {
    customElements.define(
      "mermaid-embed",
      class extends HTMLElement {
        connectedCallback() {
          const frame = document.createElement("iframe");
          frame.title = "Rendered Mermaid diagram";
          this.append(frame);
        }
      },
    );
  }
  const onLoad = vi
    .fn()
    .mockResolvedValueOnce(collection())
    .mockResolvedValueOnce(
      detail("example-diagram-one", "Example request flow"),
    );
  renderDiagramSet(onLoad);
  await screen.findByRole("list", { name: "Diagrams" });

  fireEvent.click(
    screen.getByRole("button", { name: "Preview Example request flow" }),
  );

  expect(
    await screen.findByRole("dialog", {
      name: "Example request flow preview",
    }),
  ).toBeInTheDocument();
  expect(
    await screen.findByTitle("Rendered Mermaid diagram"),
  ).toBeInTheDocument();
  expect(onLoad).toHaveBeenNthCalledWith(
    2,
    expect.objectContaining({
      href: "/siren/diagrams/example-diagram-one",
    }),
  );
});
