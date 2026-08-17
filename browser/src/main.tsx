import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { registerDiagramRenderer } from "./ui/diagram/registerDiagramRenderer";
import "@mantine/core/styles.css";
import "./styles.css";

registerDiagramRenderer();

const root = document.querySelector<HTMLDivElement>("#app");

if (!root) {
  throw new Error("The Siren Browser needs an #app element.");
}
if (!root.dataset.sirenRoot) {
  throw new Error("The Siren Browser needs a data-siren-root setting.");
}

createRoot(root).render(
  <StrictMode>
    <App rootTarget={root.dataset.sirenRoot} />
  </StrictMode>,
);
