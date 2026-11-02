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
import { diagramSvgFixtures } from "../../../stories/DiagramSvgFixtures";
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

function detail(links = [diagramSvgFixtures.link()]): Entity {
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
  loadExport.mockResolvedValue(await diagramSvgFixtures.document());
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL(file: Blob): string {
        files.push(file);
        return "blob:example-svg";
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
  ["partial document", { has_more: true }],
  ["nonzero offset", { offset: 1 }],
  ["wrong length", { total_characters: 1 }],
  ["wrong media type", { media_type: "text/html" }],
  ["empty content", { content: "" }],
  ["missing filename", { filename: undefined }],
  ["damaged digest", { content_revision: "example-corrupt" }],
])("rejects %s without saving a file", async (_name, changes) => {
  const document = await diagramSvgFixtures.document();
  loadExport.mockResolvedValue(
    sirenFixtures.entity(
      ["diagram-svg"],
      "Example SVG",
      { ...document.properties, ...changes },
      [],
      [],
      [],
    ),
  );
  render(row(async () => detail()));
  fireEvent.click(
    screen.getByRole("button", { name: "Download Example diagram as SVG" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Unable to download SVG",
  );
  expect(names).toEqual([]);
  expect(files).toEqual([]);
});

it("reports a missing advertised capability without inventing an export URL", async () => {
  render(row(async () => detail([])));
  fireEvent.click(
    screen.getByRole("button", { name: "Download Example diagram as SVG" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "SVG download is unavailable",
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
    expect(screen.getByRole("button", { name: "Download SVG" })).toBeDisabled();
  },
);

it("prevents duplicate requests and discards results when the row revision changes", async () => {
  const gate = new AbortController();
  loadExport.mockImplementation(async () => {
    await new Promise<void>((resolve) =>
      gate.signal.addEventListener("abort", () => resolve(), { once: true }),
    );
    return await diagramSvgFixtures.document();
  });
  const onLoad = vi.fn(async () => detail());
  const view = render(row(onLoad));
  const download = screen.getByRole("button", {
    name: "Download Example diagram as SVG",
  });
  fireEvent.click(download);
  fireEvent.click(download);
  await waitFor(() => expect(loadExport).toHaveBeenCalledTimes(1));
  expect(screen.getByRole("status")).toHaveTextContent(
    "Preparing Example diagram SVG",
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
    return await diagramSvgFixtures.document();
  });
  const view = render(detailView());
  fireEvent.click(screen.getByRole("button", { name: "Download SVG" }));
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
    screen.getByRole("button", { name: "Download Example diagram as SVG" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Example export temporarily unavailable",
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Retry download" }),
  );
  await waitFor(() => expect(names).toEqual(["diagram-example-r1.svg"]));
  expect(loadExport).toHaveBeenLastCalledWith(
    expect.objectContaining({
      href: "/example-exports/example?expected_revision=1",
    }),
  );
  expect(onFollow).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  const file = files[0];
  if (!file) throw new Error("No downloaded file");
  expect(file.type).toBe("image/svg+xml;charset=utf-8");
  const source = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () =>
      typeof reader.result === "string"
        ? resolve(reader.result)
        : reject(new Error("Expected SVG text"));
    reader.onerror = () => reject(new Error("Cannot read SVG"));
    reader.readAsText(file);
  });
  expect(source).toBe((await diagramSvgFixtures.document()).properties.content);
  await waitFor(() => expect(revoked).toContain("blob:example-svg"), {
    timeout: 2000,
  });
});

it("downloads the server artifact from the detail button", async () => {
  render(detailView());
  fireEvent.click(screen.getByRole("button", { name: "Download SVG" }));
  await waitFor(() => expect(names).toEqual(["diagram-example-r1.svg"]));
  expect(loadExport).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
