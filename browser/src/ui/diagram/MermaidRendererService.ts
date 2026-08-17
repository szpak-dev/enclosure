import type { MermaidConfig } from "mermaid";

export const MERMAID_CONFIGURATION = {
  deterministicIds: true,
  deterministicIDSeed: "enclosure-diagrams",
  htmlLabels: false,
  securityLevel: "strict",
  secure: [
    "deterministicIds",
    "deterministicIDSeed",
    "htmlLabels",
    "securityLevel",
    "secure",
    "startOnLoad",
  ],
  startOnLoad: false,
  suppressErrorRendering: true,
} satisfies MermaidConfig;

let mermaidPromise: Promise<(typeof import("mermaid"))["default"]> | undefined;
const activeRenders = new Map<string, Promise<string>>();

function loadMermaid(): Promise<(typeof import("mermaid"))["default"]> {
  if (!mermaidPromise) {
    mermaidPromise = import("mermaid").then(({ default: mermaid }) => {
      mermaid.initialize(MERMAID_CONFIGURATION);
      return mermaid;
    });
  }
  return mermaidPromise;
}

export function diagramSvgId(diagramId: string, revision: number): string {
  const safeId = diagramId.replace(/[^a-zA-Z0-9_-]/g, "-");
  return `diagram-${safeId}-revision-${revision}`;
}

export function renderMermaidDiagram(
  diagramId: string,
  revision: number,
  source: string,
): Promise<string> {
  const renderId = diagramSvgId(diagramId, revision);
  const renderKey = `${renderId}\u0000${source}`;
  const active = activeRenders.get(renderKey);
  if (active) return active;

  const rendering = loadMermaid()
    .then((mermaid) => mermaid.render(renderId, source))
    .then(({ svg }) => svg);
  activeRenders.set(renderKey, rendering);
  const release = () => {
    if (activeRenders.get(renderKey) === rendering)
      activeRenders.delete(renderKey);
  };
  void rendering.then(release, release);
  return rendering;
}
