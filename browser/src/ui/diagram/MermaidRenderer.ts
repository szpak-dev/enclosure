import type { RenderResult } from "mermaid";

type MermaidApplication = (typeof import("mermaid"))["default"];
export type MermaidTheme = "dark" | "default";

export class MermaidRenderer {
  private static available: Promise<void> = Promise.resolve();
  private static readonly darkThemeCompatibilityCss = `
  .treeView-node-label {
    fill: #c1c2c5 !important;
  }
  .treeView-node-line {
    stroke: #c1c2c5 !important;
  }
  `;
  private static readonly maximumSourceLength = 50_000;

  private readonly application: Promise<MermaidApplication>;

  constructor(private readonly theme: MermaidTheme) {
    this.application = import("mermaid").then(
      ({ default: application }) => application,
    );
  }

  async render(source: string, renderingId: string): Promise<RenderResult> {
    if (source.length > MermaidRenderer.maximumSourceLength) {
      throw new Error("Maximum text size in diagram exceeded.");
    }

    const rendering = MermaidRenderer.available.then(async () => {
      const application = await this.application;
      application.initialize({
        maxTextSize: MermaidRenderer.maximumSourceLength,
        securityLevel: "strict",
        startOnLoad: false,
        suppressErrorRendering: true,
        theme: this.theme,
        ...(this.theme === "dark"
          ? { themeCSS: MermaidRenderer.darkThemeCompatibilityCss }
          : {}),
      });
      return application.render(renderingId, source);
    });
    MermaidRenderer.available = rendering.then(
      () => undefined,
      () => undefined,
    );

    return rendering;
  }

  mount(container: HTMLElement, rendering: RenderResult): void {
    container.innerHTML = rendering.svg;
    const svg = container.querySelector("svg");
    if (!svg) throw new Error("Mermaid did not return a rendered SVG diagram.");

    svg.setAttribute("height", "100%");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.setAttribute("width", "100%");
    svg.style.display = "block";
    svg.style.maxWidth = "none";
    rendering.bindFunctions?.(container);
  }
}
