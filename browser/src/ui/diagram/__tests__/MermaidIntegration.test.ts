import { beforeAll, expect, it } from "vitest";
import { renderMermaidDiagram } from "../MermaidRendererService";

beforeAll(() => {
  Object.defineProperty(SVGElement.prototype, "getComputedTextLength", {
    configurable: true,
    value: () => 100,
  });
  Object.defineProperty(SVGElement.prototype, "getBBox", {
    configurable: true,
    value: () => ({ height: 20, width: 100, x: 0, y: 0 }),
  });
});

it("renders persisted Mermaid source as a non-empty SVG", async () => {
  const svg = await renderMermaidDiagram(
    "integration-diagram",
    1,
    "flowchart LR\nA[Agent] --> B[Diagram]",
  );

  expect(svg).toContain("<svg");
  expect(svg).toContain("Agent");
  expect(svg).toContain("Diagram");
});

it("does not render raw HTML or javascript links", async () => {
  const svg = await renderMermaidDiagram(
    "unsafe-diagram",
    1,
    'flowchart LR\nA["<script>window.compromised=true</script><b>Raw</b>"]\nclick A "javascript:alert(1)"',
  );

  expect(svg).not.toMatch(/<script|<foreignObject|javascript:|onclick=/i);
  expect(window).not.toHaveProperty("compromised");
});
