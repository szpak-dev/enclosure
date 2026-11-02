import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { App } from "../../app/App";

import { LanguagePreviewData } from "./LanguageStoryFixtures";

const normal = new LanguagePreviewData("normal");
const meta = {
  title: "Browser/Languages",
  component: App,
  args: { rootTarget: "/siren/" },
  parameters: { msw: { handlers: normal.handlers() } },
  beforeEach: () => normal.open("/siren/languages"),
} satisfies Meta<typeof App>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Languages: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const main = within(await canvas.findByRole("main"));
    await expect(
      await main.findByRole("link", { name: "Open Python" }),
    ).toBeVisible();
    await expect(main.getAllByRole("listitem")).toHaveLength(6);
    await expect(main.getByText("Aliases: py")).toBeVisible();
    await userEvent.click(main.getByRole("link", { name: "Open Python" }));
    await expect(
      await main.findByRole("heading", { name: "Python" }),
    ).toBeVisible();
    await expect(main.getByText(".py", { exact: true })).toBeVisible();
  },
};
export const Python: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(
      await main.findByRole("heading", { name: "Python" }),
    ).toBeVisible();
    await expect(main.getByText("python", { exact: true })).toBeVisible();
    await expect(main.getByText("py", { exact: true })).toBeVisible();
    await expect(
      main.getByRole("button", { name: "Copy language id" }),
    ).toBeVisible();
  },
  beforeEach: () => normal.open("/siren/languages/python"),
};
export const TypeScript: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(
      await main.findByRole("heading", { name: "TypeScript" }),
    ).toBeVisible();
    for (const extension of [".tsx", ".ts", ".jsx", ".js"])
      await expect(main.getByText(extension, { exact: true })).toBeVisible();
    await expect(main.getByText("ts", { exact: true })).toBeVisible();
  },
  beforeEach: () => normal.open("/siren/languages/typescript"),
};
export const NoAliases: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(await main.findByText("No aliases")).toBeVisible();
    await expect(main.getByText(".md", { exact: true })).toBeVisible();
  },
  beforeEach: () => normal.open("/siren/languages/markdown"),
};
export const NoExtensions: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(
      await main.findByText("No source extensions advertised"),
    ).toBeVisible();
    await expect(main.getByText("No aliases")).toBeVisible();
  },
  beforeEach: () => normal.open("/siren/languages/example-language"),
};

const empty = new LanguagePreviewData("empty");
export const Empty: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(await main.findByText("No languages available")).toBeVisible();
    await expect(main.queryByRole("listitem")).not.toBeInTheDocument();
    await expect(
      main.queryByRole("button", { name: /Create|New/ }),
    ).not.toBeInTheDocument();
  },
  parameters: { msw: { handlers: empty.handlers() } },
  beforeEach: () => empty.open("/siren/languages"),
};
const loading = new LanguagePreviewData("loading");
export const Loading: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(
      await main.findByRole("status", { name: "Loading resource" }),
    ).toBeVisible();
    await expect(main.queryByRole("listitem")).not.toBeInTheDocument();
  },
  parameters: { msw: { handlers: loading.handlers() } },
  beforeEach: () => loading.open("/siren/languages"),
};
const failure = new LanguagePreviewData("failure");
export const LoadFailure: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(
      await main.findByText(
        /Example language service is temporarily unavailable/,
      ),
    ).toBeVisible();
    await userEvent.click(main.getByRole("button", { name: "Retry" }));
    await expect(
      await main.findByRole("link", { name: "Open Python" }),
    ).toBeVisible();
    await expect(
      main.queryByRole("button", { name: "Retry" }),
    ).not.toBeInTheDocument();
  },
  parameters: { msw: { handlers: failure.handlers() } },
  beforeEach: () => failure.open("/siren/languages"),
};
export const DetailFailure: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(
      await main.findByText(
        /Example language service is temporarily unavailable/,
      ),
    ).toBeVisible();
    await userEvent.click(main.getByRole("button", { name: "Retry" }));
    await expect(
      await main.findByRole("heading", { name: "Python" }),
    ).toBeVisible();
    await expect(window.location.hash).toBe("#/siren/languages/python");
  },
  parameters: { msw: { handlers: failure.handlers() } },
  beforeEach: () => failure.open("/siren/languages/python"),
};
const malformed = new LanguagePreviewData("malformed");
export const IncompleteMetadata: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(
      await main.findByText("Languages view unavailable"),
    ).toBeVisible();
    await expect(main.getByText(/missing or invalid list/)).toBeVisible();
    await userEvent.click(main.getByRole("button", { name: "Reload" }));
    await expect(
      await main.findByRole("heading", { name: "Python" }),
    ).toBeVisible();
  },
  parameters: { msw: { handlers: malformed.handlers() } },
  beforeEach: () => malformed.open("/siren/languages/python"),
};
const unavailable = new LanguagePreviewData("unavailable");
export const UnavailableNavigation: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await waitFor(() =>
      expect(main.getAllByText("Navigation unavailable")).toHaveLength(6),
    );
    await expect(
      main.queryByRole("link", { name: /Open/ }),
    ).not.toBeInTheDocument();
    await expect(
      main.queryByRole("link", { name: "Python" }),
    ).not.toBeInTheDocument();
  },
  parameters: { msw: { handlers: unavailable.handlers() } },
  beforeEach: () => unavailable.open("/siren/languages"),
};
const actionOnly = new LanguagePreviewData("action-only");
export const AdvertisedGetNavigation: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await userEvent.click(
      await main.findByRole("link", { name: "Open Python" }),
    );
    await expect(
      await main.findByRole("heading", { name: "Python" }),
    ).toBeVisible();
  },
  parameters: { msw: { handlers: actionOnly.handlers() } },
  beforeEach: () => actionOnly.open("/siren/languages"),
};
const related = new LanguagePreviewData("related");
export const RelatedResource: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(
      await main.findByRole("heading", { name: "Related resources" }),
    ).toBeVisible();
    await userEvent.click(main.getByRole("link", { name: /TypeScript/ }));
    await expect(
      await main.findByRole("heading", { name: "TypeScript" }),
    ).toBeVisible();
  },
  parameters: { msw: { handlers: related.handlers() } },
  beforeEach: () => related.open("/siren/languages/python"),
};
const pagination = new LanguagePreviewData("pagination");
export const Paginated: Story = {
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await userEvent.click(await main.findByRole("link", { name: "Next page" }));
    await expect(
      await main.findByRole("link", { name: "Open Python" }),
    ).toBeVisible();
    await userEvent.click(main.getByRole("button", { name: "Reload" }));
    await expect(
      await main.findByRole("link", { name: "Open Python" }),
    ).toBeVisible();
    await expect(
      main.queryByRole("link", { name: "Open Markdown" }),
    ).not.toBeInTheDocument();
    await userEvent.click(main.getByRole("link", { name: "Next page" }));
    await expect(
      await main.findByRole("link", { name: "Open TypeScript" }),
    ).toBeVisible();
    await expect(
      main.queryByRole("link", { name: "Next page" }),
    ).not.toBeInTheDocument();
    await userEvent.click(main.getByRole("link", { name: "Previous page" }));
    await expect(
      await main.findByRole("link", { name: "Open Python" }),
    ).toBeVisible();
  },
  parameters: { msw: { handlers: pagination.handlers() } },
  beforeEach: () => pagination.open("/siren/languages"),
};

const refreshed = new LanguagePreviewData("refresh");
export const ReloadDetail: Story = {
  parameters: { msw: { handlers: refreshed.handlers() } },
  beforeEach: () => refreshed.open("/siren/languages/python"),
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(
      await main.findByRole("heading", { name: "Python" }),
    ).toBeVisible();
    await userEvent.click(main.getByRole("button", { name: "Reload" }));
    await expect(
      await main.findByRole("heading", { name: "Example refreshed language" }),
    ).toBeVisible();
  },
};
const invalidText = new LanguagePreviewData("invalid-text");
export const InvalidMetadata: Story = {
  parameters: { msw: { handlers: invalidText.handlers() } },
  beforeEach: () => invalidText.open("/siren/languages/python"),
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(
      await main.findByText(/missing or invalid text field/),
    ).toBeVisible();
    await userEvent.click(main.getByRole("button", { name: "Reload" }));
    await expect(
      await main.findByRole("heading", { name: "Python" }),
    ).toBeVisible();
  },
};
export const ReloadUnavailable: Story = {
  parameters: { msw: { handlers: unavailable.handlers() } },
  beforeEach: () => unavailable.open("/siren/languages/python"),
  play: async ({ canvasElement }) => {
    const main = within(await within(canvasElement).findByRole("main"));
    await expect(await main.findByText("Reload unavailable")).toBeVisible();
    await expect(
      main.queryByRole("button", { name: "Reload" }),
    ).not.toBeInTheDocument();
  },
};
