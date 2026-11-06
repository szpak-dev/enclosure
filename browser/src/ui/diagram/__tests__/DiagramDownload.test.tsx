import { MantineProvider } from "@mantine/core";
import type { Entity, Target } from "@siren-js/client";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { sirenFixtures } from "../../../stories/SirenFixtures";
import { diagramPngFixtures } from "../../../stories/DiagramPngFixtures";
import { DiagramDownload } from "../DiagramDownload";
import { DiagramListItem } from "../DiagramListItem";

const target = sirenFixtures.link(
  "/siren/diagrams/example",
  ["self"],
  "Example diagram",
);
const onFollow = vi.fn();
const files: Blob[] = [];
const names: string[] = [];
const revoked: string[] = [];
const loadExport = vi.fn<(target: Target) => Promise<Entity>>();

function detail(links = [diagramPngFixtures.link()]): Entity {
  return sirenFixtures.entity(
    ["diagram"],
    "Example diagram",
    {
      id: "example",
      revision: 1,
      source: "example source is never rendered for download",
    },
    [target, ...links],
    [],
    [],
  );
}

function row(onLoad: (target: Target) => Promise<Entity>, revision = 1) {
  return (
    <MantineProvider env="test" forceColorScheme="light">
      <DiagramListItem
        diagram={sirenFixtures.embeddedEntity(
          ["diagram"],
          ["item"],
          "Example diagram",
          {
            id: "example",
            kind: "flowchart",
            revision,
            title: "Example diagram",
            updated_at: "2026-10-15T08:30:00Z",
          },
          [target],
        )}
        onFollow={onFollow}
        onLoad={(requested) =>
          (typeof requested === "string"
            ? requested
            : requested.href.toString()
          ).includes("/example-exports/")
            ? loadExport(requested)
            : onLoad(requested)
        }
      />
    </MantineProvider>
  );
}

function detailView(source = "example source", entity = detail()) {
  return (
    <MantineProvider env="test" forceColorScheme="light">
      <DiagramDownload
        presentation="button"
        diagramId="example"
        revision={1}
        title="Example diagram"
        source={source}
        entity={entity}
        onLoad={loadExport}
      />
    </MantineProvider>
  );
}

beforeEach(async () => {
  files.length = 0;
  names.length = 0;
  revoked.length = 0;
  onFollow.mockClear();
  loadExport.mockReset();
  loadExport.mockResolvedValue(await diagramPngFixtures.document());
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL(file: Blob): string {
        files.push(file);
        return "blob:example-png";
      }
      static revokeObjectURL(url: string): void {
        revoked.push(url);
      }
    },
  );
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ): void {
    names.push(this.download);
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it.each([
  ["wrong diagram", { diagram_id: "example-other" }],
  ["stale revision", { revision: 2 }],
  ["wrong width", { width: 1 }],
  ["wrong height", { height: 0 }],
  ["wrong length", { total_bytes: 1 }],
  ["invalid base64", { content: "not base64!" }],
  ["invalid PNG", { content: btoa("Example invalid image payload") }],
  ["wrong media type", { media_type: "text/html" }],
  ["empty content", { content: "" }],
  ["missing filename", { filename: undefined }],
  ["damaged digest", { content_revision: "example-corrupt" }],
])("rejects %s without saving a file", async (_name, changes) => {
  const document = await diagramPngFixtures.document();
  loadExport.mockResolvedValue(
    sirenFixtures.entity(
      ["diagram-png"],
      "Example PNG",
      { ...document.properties, ...changes },
      [],
      [],
      [],
    ),
  );
  render(row(async () => detail()));
  fireEvent.click(
    screen.getByRole("button", { name: "Download Example diagram as PNG" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Unable to download PNG",
  );
  expect(names).toEqual([]);
  expect(files).toEqual([]);
});

it("reports a missing advertised capability without inventing an export URL", async () => {
  render(row(async () => detail([])));
  fireEvent.click(
    screen.getByRole("button", { name: "Download Example diagram as PNG" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "PNG download is unavailable",
  );
  expect(loadExport).not.toHaveBeenCalled();
  expect(names).toEqual([]);
});

it.each(["empty source", "missing capability"])(
  "disables detail download for %s",
  (reason) => {
    render(
      detailView(
        reason === "empty source" ? " " : "example",
        reason === "missing capability" ? detail([]) : detail(),
      ),
    );
    expect(screen.getByRole("button", { name: "Download PNG" })).toBeDisabled();
  },
);

it("prevents duplicate requests and discards results when the row revision changes", async () => {
  const gate = new AbortController();
  loadExport.mockImplementation(async () => {
    await new Promise<void>((resolve) =>
      gate.signal.addEventListener("abort", () => resolve(), { once: true }),
    );
    return await diagramPngFixtures.document();
  });
  const onLoad = vi.fn(async () => detail());
  const view = render(row(onLoad));
  const download = screen.getByRole("button", {
    name: "Download Example diagram as PNG",
  });
  fireEvent.click(download);
  fireEvent.click(download);
  await waitFor(() => expect(loadExport).toHaveBeenCalledTimes(1));
  expect(screen.getByRole("status")).toHaveTextContent(
    "Preparing Example diagram PNG",
  );
  view.rerender(row(onLoad, 2));
  await act(async () => {
    gate.abort();
  });
  expect(files).toEqual([]);
  expect(names).toEqual([]);
});

it("discards a completed response after leaving the view", async () => {
  const gate = new AbortController();
  loadExport.mockImplementation(async () => {
    await new Promise<void>((resolve) =>
      gate.signal.addEventListener("abort", () => resolve(), { once: true }),
    );
    return await diagramPngFixtures.document();
  });
  const view = render(detailView());
  fireEvent.click(screen.getByRole("button", { name: "Download PNG" }));
  await waitFor(() => expect(loadExport).toHaveBeenCalledTimes(1));
  view.unmount();
  await act(async () => {
    gate.abort();
  });
  expect(names).toEqual([]);
});

it("recovers from a server failure and saves exact advertised bytes without navigation or Preview", async () => {
  loadExport.mockRejectedValueOnce(
    new Error("Example export temporarily unavailable"),
  );
  const onLoad = vi.fn(async () => detail());
  render(row(onLoad));
  expect(onLoad).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Download Example diagram as PNG" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Example export temporarily unavailable",
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Retry download" }),
  );
  await waitFor(() => expect(names).toEqual(["diagram-example-r1.png"]));
  expect(loadExport).toHaveBeenLastCalledWith(
    expect.objectContaining({
      href: "/example-exports/example?expected_revision=1",
    }),
  );
  expect(onFollow).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  const file = files[0];
  if (!file) throw new Error("No downloaded file");
  expect(file.type).toBe("image/png");
  expect(await diagramPngFixtures.read(file)).toEqual(
    diagramPngFixtures.bytes(),
  );
  await waitFor(() => expect(revoked).toContain("blob:example-png"), {
    timeout: 2000,
  });
});

it("downloads the server artifact from the detail button", async () => {
  render(detailView());
  fireEvent.click(screen.getByRole("button", { name: "Download PNG" }));
  await waitFor(() => expect(names).toEqual(["diagram-example-r1.png"]));
  expect(loadExport).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
