import { MantineProvider } from "@mantine/core";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { Entity } from "@siren-js/client";
import { afterEach, expect, it, vi } from "vitest";
import { SirenEntity } from "../../siren/SirenEntity";
import { sirenRegistry } from "../../siren/SirenRegistry";
import { DiagramEntity } from "../DiagramEntity";

afterEach(cleanup);

vi.mock("../DiagramRenderer", () => ({
  DiagramRenderer: ({
    diagramId,
    revision,
    source,
  }: {
    diagramId: string;
    revision: number;
    source: string;
  }) => <div>{`${diagramId}:${revision}:${source}`}</div>,
}));

const diagram = {
  actions: [
    {
      fields: [],
      href: "/siren/diagrams/diagram-one",
      method: "DELETE",
      name: "delete_diagram",
      title: "Delete diagram",
    },
  ],
  class: ["diagram"],
  entities: [],
  links: [],
  properties: {
    created_at: "2026-08-14T10:00:00Z",
    diagram_set_id: "set-one",
    id: "diagram-one",
    interactions: {},
    kind: "flowchart",
    revision: 3,
    snapshot: { kind: "flowchart", version: 1 },
    source: "flowchart LR\nA-->B",
    title: "A useful diagram",
    updated_at: "2026-08-14T11:00:00Z",
  },
  title: "Diagram",
} as unknown as Entity;

function renderEntity() {
  return render(
    <MantineProvider>
      <SirenEntity
        entity={diagram}
        onFollow={vi.fn()}
        onLoad={vi.fn()}
        onSubmit={vi.fn()}
      />
    </MantineProvider>,
  );
}

it("registers and renders the specialized diagram resource with its actions", () => {
  const unregister = sirenRegistry.entities.register("diagram", DiagramEntity);
  try {
    renderEntity();

    expect(
      screen.getByRole("heading", { name: "A useful diagram" }),
    ).toBeVisible();
    expect(screen.getByText("diagram-one:3:flowchart LR A-->B")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Delete diagram" }),
    ).toBeVisible();
  } finally {
    unregister();
  }
});

it("provides source, snapshot, and metadata views", () => {
  const unregister = sirenRegistry.entities.register("diagram", DiagramEntity);
  try {
    renderEntity();

    fireEvent.click(screen.getByRole("tab", { name: "Source" }));
    expect(screen.getByText("flowchart LR A-->B")).toBeVisible();
    fireEvent.click(screen.getByRole("tab", { name: "Snapshot" }));
    expect(screen.getByText("flowchart")).toBeVisible();
    fireEvent.click(screen.getByRole("tab", { name: "Metadata" }));
    expect(screen.getByText("diagram_set_id")).toBeVisible();
    expect(screen.queryByText("source")).not.toBeInTheDocument();
  } finally {
    unregister();
  }
});
