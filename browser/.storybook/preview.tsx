import { AppProviders } from "../src/app/providers/AppProviders";
import { registerDiagramRenderer } from "../src/ui/diagram/registerDiagramRenderer";
import { registerProjectRenderers } from "../src/ui/project/registerProjectRenderers";
import { registerScaffoldingRenderers } from "../src/ui/scaffolding/registerScaffoldingRenderers";
import { registerRecordRenderers } from "../src/ui/records/registerRecordRenderers";
import { registerLanguageRenderers } from "../src/ui/language/registerLanguageRenderers";
import type { Preview } from "@storybook/react-vite";
import { mswLoader } from "msw-storybook-addon/csf3";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "../src/styles.css";

registerDiagramRenderer();
registerProjectRenderers();
registerScaffoldingRenderers();
registerRecordRenderers();
registerLanguageRenderers();

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
