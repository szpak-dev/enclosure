import { MantineProvider } from "@mantine/core";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DiagramRenderer } from "../DiagramRenderer";

const renderMermaidDiagram = vi.hoisted(() => vi.fn());
const source = "flowchart LR\nA-->B";

vi.mock("../MermaidRendererService", () => ({ renderMermaidDiagram }));

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

function renderDiagram(
  properties: Partial<React.ComponentProps<typeof DiagramRenderer>> = {},
) {
  return render(
    <MantineProvider>
      <DiagramRenderer
        diagramId="diagram-one"
        revision={1}
        source={source}
        {...properties}
      />
    </MantineProvider>,
  );
}

it("shows loading before inserting a non-empty SVG", async () => {
  let finish: (value: string) => void = () => undefined;
  renderMermaidDiagram.mockReturnValue(
    new Promise<string>((resolve) => {
      finish = resolve;
    }),
  );

  renderDiagram();

  expect(screen.getByRole("status")).toHaveTextContent("Rendering diagram");
  finish('<svg data-rendered="true"><title>Example</title></svg>');

  const rendered = await screen.findByRole("img", { name: "Rendered diagram" });
  expect(rendered.querySelector("svg")).not.toBeNull();
});

it("shows an empty-source state without invoking Mermaid", () => {
  renderDiagram({ source: "  " });

  expect(screen.getByText("Diagram has no source")).toBeVisible();
  expect(renderMermaidDiagram).not.toHaveBeenCalled();
});

it("shows Mermaid syntax failures", async () => {
  renderMermaidDiagram.mockRejectedValue(new Error("Parse error on line 2"));

  renderDiagram({ source: "not a diagram" });

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Unable to render diagramParse error on line 2",
  );
});

it("renders again when the persisted revision changes", async () => {
  renderMermaidDiagram.mockResolvedValue("<svg></svg>");
  const view = renderDiagram();
  await screen.findByRole("img");

  view.rerender(
    <MantineProvider>
      <DiagramRenderer diagramId="diagram-one" revision={2} source={source} />
    </MantineProvider>,
  );

  await waitFor(() =>
    expect(renderMermaidDiagram).toHaveBeenLastCalledWith(
      "diagram-one",
      2,
      source,
    ),
  );
  expect(renderMermaidDiagram).toHaveBeenCalledTimes(2);
});
