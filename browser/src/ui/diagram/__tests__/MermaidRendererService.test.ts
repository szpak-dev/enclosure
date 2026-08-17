import { expect, it, vi } from "vitest";
import {
  diagramSvgId,
  MERMAID_CONFIGURATION,
  renderMermaidDiagram,
} from "../MermaidRendererService";

const mermaid = vi.hoisted(() => ({
  initialize: vi.fn(),
  render: vi.fn().mockResolvedValue({ svg: "<svg>diagram</svg>" }),
}));

vi.mock("mermaid", () => ({ default: mermaid }));

it("renders with the locked-down Mermaid configuration and a deterministic id", async () => {
  const first = renderMermaidDiagram("diagram/one", 7, "flowchart LR\nA-->B");
  const duplicate = renderMermaidDiagram(
    "diagram/one",
    7,
    "flowchart LR\nA-->B",
  );

  await expect(first).resolves.toBe("<svg>diagram</svg>");
  await expect(duplicate).resolves.toBe("<svg>diagram</svg>");
  expect(diagramSvgId("diagram/one", 7)).toBe("diagram-diagram-one-revision-7");
  expect(mermaid.initialize).toHaveBeenCalledWith(MERMAID_CONFIGURATION);
  expect(MERMAID_CONFIGURATION).toMatchObject({
    deterministicIds: true,
    htmlLabels: false,
    securityLevel: "strict",
    startOnLoad: false,
    suppressErrorRendering: true,
  });
  expect(mermaid.render).toHaveBeenCalledTimes(1);
  expect(mermaid.render).toHaveBeenCalledWith(
    "diagram-diagram-one-revision-7",
    "flowchart LR\nA-->B",
  );
});
