import type { Entity, Target } from "@siren-js/client";
import { scaffoldingPresentation } from "./ScaffoldingPresentation";

export type TemplateInput = {
  content: string;
  path: string;
  write_mode: string;
};

export class ScaffoldingTemplateHydrator {
  constructor(private readonly load: (target: Target) => Promise<Entity>) {}

  async hydrate(target: Target): Promise<readonly TemplateInput[]> {
    const templates: TemplateInput[] = [];
    let page = await this.load(target);
    const revision = scaffoldingPresentation.string(
      page.properties,
      "revision",
    );
    if (!revision)
      throw new Error("The template manifest is missing its pinned revision.");
    while (true) {
      if (
        scaffoldingPresentation.string(page.properties, "revision") !== revision
      )
        throw new Error(
          "The template manifest revision changed during hydration.",
        );
      const targets = page.entities.map((item) =>
        scaffoldingPresentation.itemTarget(item),
      );
      if (targets.some((candidate) => candidate.kind === "absent"))
        throw new Error(
          "At least one template manifest does not advertise its revision-pinned content.",
        );
      const contents = await Promise.all(
        targets.map((candidate) => {
          if (candidate.kind === "absent")
            throw new Error("Template content target unavailable.");
          return this.hydrateTemplate(candidate.target);
        }),
      );
      templates.push(...contents);
      const next = page.links.find((link) => link.rel.includes("next"));
      if (!next) return templates;
      page = await this.load(next);
    }
  }

  private async hydrateTemplate(target: Target): Promise<TemplateInput> {
    let page = await this.load(target);
    const path = scaffoldingPresentation.string(page.properties, "path");
    const writeMode = scaffoldingPresentation.string(
      page.properties,
      "write_mode",
    );
    const revision = scaffoldingPresentation.string(
      page.properties,
      "revision",
    );
    if (!path || !writeMode || !revision)
      throw new Error(
        "A template document is missing its path, write mode, or revision.",
      );
    let content = "";
    while (true) {
      if (
        scaffoldingPresentation.string(page.properties, "path") !== path ||
        scaffoldingPresentation.string(page.properties, "write_mode") !==
          writeMode ||
        scaffoldingPresentation.string(page.properties, "revision") !== revision
      )
        throw new Error(
          `Template ${path} changed identity during bounded hydration.`,
        );
      const chunk = scaffoldingPresentation.string(page.properties, "content");
      if (chunk === undefined)
        throw new Error(`Template ${path} returned malformed content.`);
      content += chunk;
      const next = page.links.find((link) => link.rel.includes("next"));
      if (!next) return { content, path, write_mode: writeMode };
      page = await this.load(next);
    }
  }
}
