import type { StorybookConfig } from "@storybook/react-vite";

const config = {
  addons: [
    "@storybook/addon-docs",
    "@storybook/addon-a11y",
    "@storybook/addon-vitest",
    "@storybook/addon-mcp",
    "msw-storybook-addon",
  ],
  features: {
    componentsManifest: true,
  },
  framework: {
    name: "@storybook/react-vite",
    options: {},
  },
  stories: ["../src/**/*.stories.@(ts|tsx)"],
  staticDirs: ["./public"],
} satisfies StorybookConfig;

export default config;
