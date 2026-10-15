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

const source = "flowchart LR\nExampleA-->ExampleB";

afterEach(() => {
  cleanup();
  document
    .querySelectorAll("script[data-mermaid-embed-loader]")
    .forEach((script) => script.remove());
});

function renderDiagram(sourceValue = source) {
  return render(
    <MantineProvider>
      <DiagramRenderer
        diagramId="example-diagram"
        revision={1}
        source={sourceValue}
        title="Example diagram"
      />
    </MantineProvider>,
  );
}

it("reports a Mermaid viewer load failure inside the full-screen preview", async () => {
  renderDiagram();

  fireEvent.click(screen.getByRole("button", { name: "Preview diagram" }));
  const script = await waitFor(() => {
    const candidate = document.querySelector<HTMLScriptElement>(
      "script[data-mermaid-embed-loader]",
    );
    if (!candidate) throw new Error("Mermaid viewer script was not requested.");
    return candidate;
  });
  fireEvent.error(script);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Mermaid's embedded viewer could not be loaded.",
  );
  expect(
    screen.getByRole("dialog", { name: "Example diagram preview" }),
  ).toBeVisible();
});

it("reports an empty diagram only after its preview is opened", async () => {
  renderDiagram("  ");

  expect(screen.queryByText("Diagram has no source")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Preview diagram" }));

  expect(await screen.findByText("Diagram has no source")).toBeInTheDocument();
  expect(
    document.querySelector("script[data-mermaid-embed-loader]"),
  ).toBeNull();
});

it("opens the official Mermaid embed in a full-screen preview", async () => {
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
  renderDiagram();

  fireEvent.click(screen.getByRole("button", { name: "Preview diagram" }));

  const embed = await waitFor(() => {
    const candidate = document.querySelector("mermaid-embed");
    if (!candidate) throw new Error("Mermaid embed was not displayed.");
    return candidate;
  });
  expect(
    await screen.findByRole("dialog", { name: "Example diagram preview" }),
  ).toBeInTheDocument();
  expect(embed).toHaveAttribute("src", "https://mermaid.live/embed");
  expect(embed).toHaveAttribute("controls", "1");
  expect(embed).toHaveAttribute("grid", "1");
  expect(screen.getByTitle("Rendered Mermaid diagram")).toBeInTheDocument();
  expect(document.querySelector("pre")).toBeNull();
});
