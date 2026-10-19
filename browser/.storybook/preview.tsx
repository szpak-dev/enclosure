import { AppProviders } from "../src/app/providers/AppProviders";
import { registerDiagramRenderer } from "../src/ui/diagram/registerDiagramRenderer";
import { registerProjectRenderers } from "../src/ui/project/registerProjectRenderers";
import { registerScaffoldingRenderers } from "../src/ui/scaffolding/registerScaffoldingRenderers";
import type { Preview } from "@storybook/react-vite";
import { mswLoader } from "msw-storybook-addon/csf3";
import "@mantine/core/styles.css";
import "../src/styles.css";

registerDiagramRenderer();
registerProjectRenderers();
registerScaffoldingRenderers();

const preview = {
  decorators: [
    (Story) => (
      <AppProviders>
        <Story />
      </AppProviders>
    ),
  ],
  loaders: [mswLoader()],
  parameters: {
    a11y: {
      test: "error",
    },
    layout: "fullscreen",
  },
} satisfies Preview;

export default preview;
