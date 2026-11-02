import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";

import { RecordsPreview } from "./RecordsPreview";
import { RecordsPreviewData } from "./RecordsPreviewData";

const normal = new RecordsPreviewData("normal");
const meta = {
  title: "Browser/Records",
  component: RecordsPreview,
  args: { initial: "records", scenario: "normal" },
  parameters: { msw: { handlers: normal.handlers() } },
  beforeEach: () => normal.reset(),
} satisfies Meta<typeof RecordsPreview>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Records: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(
      canvas.getByRole("textbox", { name: /Describe/ }),
      "example decisions",
    );
    await userEvent.click(canvas.getByRole("button", { name: "Search" }));
    await expect(await canvas.findByText(/Results for/)).toBeVisible();
    await userEvent.click(canvas.getByRole("button", { name: /Clear/ }));
    await expect(canvas.getByRole("textbox", { name: /Describe/ })).toHaveValue(
      "",
    );
    await userEvent.click(
      canvas.getByRole("link", { name: "Open Example decisions" }),
    );
    await expect(
      await canvas.findByRole("heading", { name: "Example decisions" }),
    ).toBeVisible();
  },
};
export const EmptyRecords: Story = {
  play: async ({ canvasElement }) => {
    await expect(
      within(canvasElement).getByText("No records yet"),
    ).toBeVisible();
  },
  args: { scenario: "empty" },
  parameters: { msw: { handlers: new RecordsPreviewData("empty").handlers() } },
};
export const RecordDetails: Story = {
  args: { initial: "record" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      await canvas.findByText(
        "A shared place for project decisions and supporting material.",
      ),
    ).toBeVisible();
    await userEvent.click(canvas.getByRole("radio", { name: "JSON" }));
    await expect(canvas.getByText(/"summary":/)).toBeVisible();
    await userEvent.click(canvas.getByRole("radio", { name: "Reading" }));
    await userEvent.click(
      canvas.getByRole("button", { name: "Open examples/notes.md" }),
    );
    await expect(await canvas.findByText(/Example notes/)).toBeVisible();
  },
};
export const CreateRecord: Story = {
  args: { initial: "new" },
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.type(
      await body.findByRole("textbox", { name: "Title" }),
      "Example new record",
    );
    await userEvent.click(body.getByRole("combobox", { name: "Category" }));
    await userEvent.click(
      await body.findByRole("option", { name: "Decisions" }),
    );
    await userEvent.click(body.getByRole("combobox", { name: "Tags" }));
    await userEvent.click(
      await body.findByRole("option", { name: "example-reviewed" }),
    );
    await userEvent.keyboard("{Escape}");
    await userEvent.type(
      await body.findByRole("textbox", { name: /Summary/ }),
      "Example content",
    );
    await userEvent.click(body.getByRole("button", { name: "Create record" }));
    await waitFor(() =>
      expect(normal.writes).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Example new record",
          category_id: "example-decisions",
          tag_ids: ["example-reviewed"],
          resources: [],
          content: { summary: "Example content" },
        }),
      ),
    );
    await expect(
      await body.findByRole("heading", { name: "Example new record" }),
    ).toBeVisible();
  },
};
export const EditRecord: Story = {
  args: { initial: "editor" },
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    const title = await body.findByRole("textbox", {
      name: "Title",
    });
    await waitFor(() =>
      expect(body.getByRole("button", { name: "Save changes" })).toBeEnabled(),
    );
    await userEvent.clear(title);
    await userEvent.click(body.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(title).toHaveFocus());
    await expect(normal.writes).not.toHaveBeenCalled();
    await userEvent.type(title, "Example revised record");
    await userEvent.click(body.getByRole("button", { name: "Cancel" }));
    await waitFor(() =>
      expect(
        body.getByRole("dialog", { name: "Discard unsaved changes?" }),
      ).toBeVisible(),
    );
    await userEvent.click(body.getByRole("button", { name: "Keep editing" }));
    await userEvent.click(body.getByRole("button", { name: "Save changes" }));
    await waitFor(() =>
      expect(normal.writes).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Example revised record",
          category_id: "example-notes",
          tag_ids: ["example-reference", "example-reviewed"],
          content: normal.content,
          resources: [
            {
              path: "examples/notes.md",
              language: "markdown",
              content: normal.source,
            },
          ],
        }),
      ),
    );
    await expect(
      await body.findByRole("heading", { name: "Example revised record" }),
    ).toBeVisible();
  },
};
export const HistoricalSchema: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await expect(
      await body.findByText("JSON editing for this schema version"),
    ).toBeVisible();
    await expect(
      body.getByRole("textbox", { name: "Content JSON" }),
    ).toHaveValue(JSON.stringify(normal.content, null, 2));
    await expect(
      body.queryByRole("radio", { name: "Fields" }),
    ).not.toBeInTheDocument();
  },
  args: { initial: "editor", scenario: "historical" },
  parameters: {
    msw: { handlers: new RecordsPreviewData("historical").handlers() },
  },
};
export const PreparingEditor: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await expect(
      await body.findByRole("status", { name: "Preparing editor" }),
    ).toBeVisible();
    await expect(
      body.queryByRole("button", { name: "Save changes" }),
    ).not.toBeInTheDocument();
  },
  args: { initial: "editor", scenario: "loading" },
  parameters: {
    msw: { handlers: new RecordsPreviewData("loading").handlers() },
  },
};
const loadFailureData = new RecordsPreviewData("load-failure");
export const ResourceLoadFailure: Story = {
  beforeEach: () => loadFailureData.reset(),
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await expect(await body.findByText("Editor unavailable")).toBeVisible();
    await expect(
      body.queryByRole("button", { name: "Save changes" }),
    ).not.toBeInTheDocument();
    loadFailureData.recover();
    await userEvent.click(
      body.getByRole("button", { name: "Reload and retry" }),
    );
    await waitFor(() =>
      expect(body.getByRole("button", { name: "Save changes" })).toBeEnabled(),
    );
  },
  args: { initial: "editor", scenario: "load-failure" },
  parameters: {
    msw: { handlers: loadFailureData.handlers() },
  },
};
export const StaleResources: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await expect(
      await body.findByText(/Resource content changed/),
    ).toBeVisible();
    await expect(
      body.queryByRole("button", { name: "Save changes" }),
    ).not.toBeInTheDocument();
  },
  args: { initial: "editor", scenario: "stale" },
  parameters: { msw: { handlers: new RecordsPreviewData("stale").handlers() } },
};
export const Categories: Story = {
  args: { initial: "categories" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("link", { name: "Next page" }));
    await expect(
      await canvas.findByRole("button", { name: "Open Decisions" }),
    ).toBeVisible();
    await userEvent.click(
      canvas.getByRole("button", { name: "Open Decisions" }),
    );
    await expect(
      await canvas.findByRole("heading", { name: "Decisions" }),
    ).toBeVisible();
  },
};
export const CategoryDetails: Story = {
  args: { initial: "category" },
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(
      await body.findByRole("button", { name: "More actions" }),
    );
    await userEvent.click(
      await body.findByRole("menuitem", { name: "Edit schema" }),
    );
    const dialog = await body.findByRole("dialog", { name: "Edit schema" });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Edit schema" }),
    );
    await expect(
      await within(dialog).findByText("Schema v3 saved"),
    ).toBeVisible();
    await expect(
      within(dialog).getByText(
        "Existing records keep their assigned schema version.",
      ),
    ).toBeVisible();
    await expect(normal.writes).toHaveBeenCalledWith({
      content_schema: normal.schema,
    });
  },
};
export const Tags: Story = {
  args: { initial: "tags" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(
      canvas.getByRole("link", { name: "example-reference" }),
    );
    await expect(
      await canvas.findByRole("button", { name: "Rename tag" }),
    ).toBeVisible();
  },
};
export const TagDetails: Story = {
  args: { initial: "tag" },
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(body.getByRole("button", { name: "Rename tag" }));
    const dialog = await body.findByRole("dialog", { name: "Rename tag" });
    const field = within(dialog).getByRole("textbox", { name: "Name" });
    await userEvent.clear(field);
    await userEvent.type(field, "example-renamed");
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Rename tag" }),
    );
    await expect(
      await within(dialog).findByText("example-renamed"),
    ).toBeVisible();
    await expect(normal.writes).toHaveBeenCalledWith({
      name: "example-renamed",
    });
  },
};
export const Resources: Story = {
  args: { initial: "resources" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("examples/notes.md")).toBeVisible();
    await userEvent.click(
      canvas.getByRole("button", { name: "Open examples/notes.md" }),
    );
    await expect(await canvas.findByText(/Example notes/)).toBeVisible();
  },
};
export const SourcePages: Story = {
  args: { initial: "source" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText(/Characters 0–35/)).toBeVisible();
    await userEvent.click(canvas.getByRole("link", { name: /Next/ }));
    await expect(await canvas.findByText(/Characters 35–70/)).toBeVisible();
    await userEvent.click(canvas.getByRole("link", { name: /Next/ }));
    await expect(await canvas.findByText(/Characters 70–/)).toBeVisible();
    await expect(
      canvas.queryByRole("link", { name: /Next/ }),
    ).not.toBeInTheDocument();
  },
};
export const ProtectedRecord: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(body.getByRole("button", { name: "Delete record" }));
    await userEvent.click(
      await body.findByRole("button", { name: "Continue" }),
    );
    const dialog = await body.findByRole("dialog", { name: "Delete record" });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Delete record" }),
    );
    await expect(
      await body.findByText("Action could not proceed", { exact: true }),
    ).toBeVisible();
    await expect(
      body.getByRole("heading", { name: "Example decisions", hidden: true }),
    ).toBeInTheDocument();
  },
  args: { initial: "record", scenario: "protected" },
  parameters: {
    msw: { handlers: new RecordsPreviewData("protected").handlers() },
  },
};
export const ApprovalRequired: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(body.getByRole("button", { name: "Delete record" }));
    await userEvent.click(
      await body.findByRole("button", { name: "Continue" }),
    );
    const dialog = await body.findByRole("dialog", { name: "Delete record" });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Delete record" }),
    );
    await expect(
      await body.findByText("One-time approval required", { exact: true }),
    ).toBeVisible();
    await expect(
      body.getByRole("heading", { name: "Example decisions", hidden: true }),
    ).toBeInTheDocument();
  },
  args: { initial: "record", scenario: "approval" },
  parameters: {
    msw: { handlers: new RecordsPreviewData("approval").handlers() },
  },
};

const retryData = new RecordsPreviewData("save-failure");
export const SaveFailure: Story = {
  args: { initial: "editor", scenario: "save-failure" },
  parameters: { msw: { handlers: retryData.handlers() } },
  beforeEach: () => retryData.reset(),
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    const title = await body.findByRole("textbox", {
      name: "Title",
    });
    await waitFor(() =>
      expect(body.getByRole("button", { name: "Save changes" })).toBeEnabled(),
    );
    await userEvent.clear(title);
    await userEvent.type(title, "Example preserved draft");
    await userEvent.click(body.getByRole("button", { name: "Save changes" }));
    await expect(
      await body.findByText(/Example temporary failure/),
    ).toBeVisible();
    await expect(title).toHaveValue("Example preserved draft");
    await userEvent.click(body.getByRole("button", { name: "Save changes" }));
    await expect(
      await body.findByRole("heading", { name: "Example preserved draft" }),
    ).toBeVisible();
    await expect(retryData.writes).toHaveBeenCalledTimes(2);
    await expect(retryData.writes.mock.calls[0]).toEqual(
      retryData.writes.mock.calls[1],
    );
  },
};

const deleteData = new RecordsPreviewData("delete-success");
export const DeleteRecord: Story = {
  args: { initial: "record", scenario: "delete-success" },
  parameters: { msw: { handlers: deleteData.handlers() } },
  beforeEach: () => deleteData.reset(),
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await userEvent.click(body.getByRole("button", { name: "Delete record" }));
    await userEvent.click(
      await body.findByRole("button", { name: "Continue" }),
    );
    const dialog = await body.findByRole("dialog", { name: "Delete record" });
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Delete record" }),
    );
    await expect(
      await within(canvasElement).findByText("No records yet"),
    ).toBeVisible();
  },
};

export const EmptySearch: Story = {
  args: { scenario: "search-empty" },
  parameters: {
    msw: { handlers: new RecordsPreviewData("search-empty").handlers() },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(
      canvas.getByRole("textbox", { name: /Describe/ }),
      "example missing record",
    );
    await userEvent.click(canvas.getByRole("button", { name: "Search" }));
    await expect(await canvas.findByText("No matching records")).toBeVisible();
    await userEvent.click(canvas.getByRole("button", { name: /Clear/ }));
    await expect(
      canvas.getByRole("link", { name: "Open Example decisions" }),
    ).toBeVisible();
  },
};
const searchFailureData = new RecordsPreviewData("search-failure");
export const SearchFailure: Story = {
  args: { scenario: "search-failure" },
  parameters: { msw: { handlers: searchFailureData.handlers() } },
  beforeEach: () => searchFailureData.reset(),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const query = canvas.getByRole("textbox", { name: /Describe/ });
    await userEvent.type(query, "example decisions");
    await userEvent.click(canvas.getByRole("button", { name: "Search" }));
    await expect(
      await canvas.findByText(/Example search service unavailable/),
    ).toBeVisible();
    await expect(query).toHaveValue("example decisions");
    searchFailureData.recover();
    await userEvent.click(canvas.getByRole("button", { name: "Retry search" }));
    await expect(await canvas.findByText(/Results for/)).toBeVisible();
    await expect(
      canvas.getByRole("link", { name: "Open Example decisions" }),
    ).toBeVisible();
  },
};
