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
import { DiagramListItem } from "../DiagramListItem";
import { DiagramRenderer } from "../DiagramRenderer";

const target = sirenFixtures.link(
  "/siren/diagrams/example",
  ["self"],
  "Example diagram",
);
const summary = sirenFixtures.embeddedEntity(
  ["diagram"],
  ["item"],
  "Example diagram",
  {
    id: "example",
    kind: "flowchart-v2",
    revision: 1,
    title: "Example diagram",
    updated_at: "2026-10-15T08:30:00Z",
  },
  [target],
);
const validSource = "flowchart LR\nExampleA-->ExampleB";
const onFollow = vi.fn();
const files: Blob[] = [];
const names: string[] = [];
const revoked: string[] = [];

function detail(source: string): Entity {
  return sirenFixtures.entity(
    ["diagram"],
    "Example diagram",
    {
      id: "example",
      revision: 2,
      source,
    },
    [target],
    [],
    [],
  );
}

function row(
  onLoad: (target: Target) => Promise<Entity>,
  revision: number = 1,
) {
  return (
    <MantineProvider env="test" forceColorScheme="light">
      <DiagramListItem
        diagram={sirenFixtures.embeddedEntity(
          ["diagram"],
          ["item"],
          "Example diagram",
          { ...summary.properties, revision },
          [target],
        )}
        onFollow={onFollow}
        onLoad={onLoad}
      />
    </MantineProvider>
  );
}

function detailView(source: string) {
  return (
    <MantineProvider env="test" forceColorScheme="light">
      <DiagramRenderer
        diagramId="example"
        revision={2}
        source={source}
        title="Example diagram"
      />
    </MantineProvider>
  );
}

beforeEach(() => {
  files.length = 0;
  names.length = 0;
  revoked.length = 0;
  onFollow.mockClear();
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
  [
    "missing source",
    sirenFixtures.entity(
      ["diagram"],
      "Example",
      { id: "example", revision: 2 },
      [],
      [],
      [],
    ),
    "does not contain SVG rendering data",
  ],
  ["empty source", detail(" "), "Diagram has no source"],
  [
    "invalid source",
    detail("flowchart LR\nExampleA-->"),
    "Unable to download SVG",
  ],
] as const)(
  "rejects %s without downloading",
  async (_name, entity, message) => {
    render(row(async () => entity));
    fireEvent.click(
      screen.getByRole("button", { name: "Download Example diagram as SVG" }),
    );
    expect(
      await screen.findByRole("alert", {}, { timeout: 15000 }),
    ).toHaveTextContent(message);
    expect(names).toEqual([]);
    expect(files).toEqual([]);
  },
);

it("disables detail download for empty source", () => {
  render(detailView("  "));
  expect(screen.getByRole("button", { name: "Download SVG" })).toBeDisabled();
});

it("recovers from a lazy-loading failure and downloads without navigating or opening Preview", async () => {
  const onLoad = vi
    .fn<(target: Target) => Promise<Entity>>()
    .mockRejectedValueOnce(new Error("Example connection unavailable"))
    .mockResolvedValueOnce(detail(validSource));
  render(row(onLoad));
  expect(onLoad).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Download Example diagram as SVG" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Example connection unavailable",
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Retry download" }),
  );
  await waitFor(() => expect(names).toEqual(["diagram-example-r2.svg"]), {
    timeout: 15000,
  });
  expect(onLoad).toHaveBeenCalledTimes(2);
  expect(onLoad).toHaveBeenLastCalledWith(target);
  expect(onFollow).not.toHaveBeenCalled();
  expect(
    screen.queryByRole("dialog", { name: "Example diagram preview" }),
  ).not.toBeInTheDocument();
  const file = files[0];
  if (!file) throw new Error("The browser did not receive an SVG file.");
  expect(file.type).toBe("image/svg+xml;charset=utf-8");
  const source = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () =>
      typeof reader.result === "string"
        ? resolve(reader.result)
        : reject(new Error("Expected SVG text"));
    reader.onerror = () => reject(new Error("Cannot read downloaded SVG"));
    reader.readAsText(file);
  });
  const svg = new DOMParser().parseFromString(source, "image/svg+xml");
  expect(svg.querySelector("parsererror")).toBeNull();
  expect(svg.documentElement.localName).toBe("svg");
  expect(svg.documentElement.getAttribute("viewBox")).toBeTruthy();
  expect(svg.documentElement.textContent).toContain("ExampleA");
  expect(svg.documentElement.textContent).toContain("ExampleB");
  await waitFor(() => expect(revoked).toContain("blob:example-svg"), {
    timeout: 2000,
  });
});

it("prevents duplicate requests and discards a download when its row revision changes", async () => {
  const gate = new AbortController();
  const onLoad = vi.fn(async (): Promise<Entity> => {
    await new Promise<void>((resolve) =>
      gate.signal.addEventListener("abort", () => resolve(), { once: true }),
    );
    return detail(validSource);
  });
  const view = render(row(onLoad));
  const download = screen.getByRole("button", {
    name: "Download Example diagram as SVG",
  });
  fireEvent.click(download);
  fireEvent.click(download);
  expect(onLoad).toHaveBeenCalledTimes(1);
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

it("downloads directly from the detail view without opening Preview", async () => {
  render(detailView(validSource));
  fireEvent.click(screen.getByRole("button", { name: "Download SVG" }));
  await waitFor(() => expect(names).toEqual(["diagram-example-r2.svg"]), {
    timeout: 15000,
  });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await waitFor(() => expect(revoked).toContain("blob:example-svg"), {
    timeout: 2000,
  });
});
