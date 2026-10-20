import { MantineProvider } from "@mantine/core";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { DiagramRenderer } from "../DiagramRenderer";

const validSource = "flowchart LR\nExampleA-->ExampleB";
const treeViewSource = "treeView-beta\nroot/\n  child.ts";
const mermaidRenderingTimeout = 15_000;

afterEach(() => {
  cleanup();
});

function diagram(
  source: string,
  revision = 1,
  colorScheme: "dark" | "light" = "light",
) {
  return (
    <MantineProvider forceColorScheme={colorScheme}>
      <DiagramRenderer
        diagramId="example-diagram"
        revision={revision}
        source={source}
        title="Example diagram"
      />
    </MantineProvider>
  );
}

function renderDiagram(source = validSource) {
  return render(diagram(source));
}

async function openPreview() {
  fireEvent.click(screen.getByRole("button", { name: "Preview diagram" }));
  expect(
    await screen.findByRole("dialog", { name: "Example diagram preview" }),
  ).toBeInTheDocument();
}

it("rejects invalid Mermaid source inside the public preview", async () => {
  renderDiagram("flowchart LR\nExampleA-->");
  await openPreview();

  expect(
    await screen.findByRole("alert", undefined, {
      timeout: mermaidRenderingTimeout,
    }),
  ).toHaveTextContent("Unable to render Mermaid preview");
});

it("rejects Mermaid source beyond the configured text limit", async () => {
  renderDiagram(`flowchart LR\n${"A".repeat(50_001)}`);
  await openPreview();

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Maximum text size in diagram exceeded",
  );
});

it("reports an empty diagram only after its preview is opened", async () => {
  renderDiagram("  ");

  expect(screen.queryByText("Diagram has no source")).not.toBeInTheDocument();
  await openPreview();

  expect(screen.getByText("Diagram has no source")).toBeInTheDocument();
  expect(screen.queryByRole("img")).toBeNull();
});

it("removes the rendered diagram when the preview is closed", async () => {
  renderDiagram();
  await openPreview();

  const preview = await screen.findByRole("img", {
    name: "Example diagram Mermaid preview",
  });
  await waitFor(() => expect(preview.querySelector("svg")).not.toBeNull());

  fireEvent.click(
    screen.getByRole("button", { name: "Close Example diagram preview" }),
  );

  await waitFor(() =>
    expect(
      screen.queryByRole("dialog", { name: "Example diagram preview" }),
    ).toBeNull(),
  );
  expect(screen.queryByRole("img")).toBeNull();
});

it("recovers when invalid source is replaced by a valid revision", async () => {
  const rendered = renderDiagram("flowchart LR\nExampleA-->");
  await openPreview();
  expect(await screen.findByRole("alert")).toBeVisible();

  fireEvent.click(
    screen.getByRole("button", { name: "Close Example diagram preview" }),
  );
  await waitFor(() =>
    expect(
      screen.queryByRole("dialog", { name: "Example diagram preview" }),
    ).toBeNull(),
  );
  rendered.rerender(diagram(validSource, 2));
  await openPreview();

  const preview = await screen.findByRole("img", {
    name: "Example diagram Mermaid preview",
  });
  await waitFor(() => expect(preview.querySelector("svg")).not.toBeNull());
  expect(screen.queryByRole("alert")).toBeNull();
});

it("renders valid Mermaid source locally in the public preview", async () => {
  renderDiagram();
  await openPreview();

  const preview = await screen.findByRole("img", {
    name: "Example diagram Mermaid preview",
  });
  await waitFor(() => expect(preview.querySelector("svg")).not.toBeNull());
  expect(
    screen.getByRole("toolbar", { name: "Diagram zoom controls" }),
  ).toBeVisible();
  expect(screen.getByLabelText("Zoom level")).toHaveTextContent("100%");

  fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
  expect(screen.getByLabelText("Zoom level")).toHaveTextContent("125%");
  fireEvent.keyDown(preview, { key: "ArrowLeft" });
  expect(preview.firstElementChild).toHaveStyle({
    transform: "translate3d(40px, 0px, 0) scale(1.25)",
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Center and fit diagram" }),
  );
  expect(screen.getByLabelText("Zoom level")).toHaveTextContent("100%");
  expect(preview.firstElementChild).toHaveStyle({
    transform: "translate3d(0px, 0px, 0) scale(1)",
  });
  expect(preview.querySelector("svg")).toHaveAttribute("height", "100%");
  expect(preview.querySelector("svg")).toHaveAttribute("width", "100%");
  expect(preview.querySelector("svg")).toHaveStyle({
    display: "block",
    maxWidth: "none",
  });
  expect(document.querySelector("iframe")).toBeNull();
  expect(
    document.querySelector("script[data-mermaid-embed-loader]"),
  ).toBeNull();
});

it("renders with Mermaid's dark palette when the application is dark", async () => {
  render(diagram(treeViewSource, 1, "dark"));
  await openPreview();

  const preview = await screen.findByRole("img", {
    name: "Example diagram Mermaid preview",
  });
  await waitFor(() => expect(preview.querySelector("svg")).not.toBeNull());
  const label = preview.querySelector(".treeView-node-label");
  const line = preview.querySelector(".treeView-node-line");
  expect(label).not.toBeNull();
  expect(line).not.toBeNull();
  if (!label || !line)
    throw new Error("Dark tree did not expose its visible labels and lines.");
  expect(getComputedStyle(label).fill).toBe("rgb(193, 194, 197)");
  expect(getComputedStyle(line).stroke).toBe("rgb(193, 194, 197)");
});
