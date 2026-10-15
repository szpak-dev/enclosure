export class MermaidEmbedLoader {
  private readonly elementName = "mermaid-embed";
  private readonly scriptSelector = "script[data-mermaid-embed-loader]";
  private readonly scriptUrl = "https://mermaid.live/embed.js";

  load(): Promise<void> {
    if (customElements.get(this.elementName)) return Promise.resolve();

    const existing = document.querySelector<HTMLScriptElement>(
      this.scriptSelector,
    );
    const script = existing ?? document.createElement("script");

    return new Promise((resolve, reject) => {
      const loaded = () => {
        void customElements.whenDefined(this.elementName).then(() => resolve());
      };
      const failed = () => {
        script.remove();
        reject(new Error("Mermaid's embedded viewer could not be loaded."));
      };

      script.addEventListener("load", loaded, { once: true });
      script.addEventListener("error", failed, { once: true });

      if (!existing) {
        script.async = true;
        script.dataset.mermaidEmbedLoader = "true";
        script.src = this.scriptUrl;
        document.head.append(script);
      }
    });
  }
}
