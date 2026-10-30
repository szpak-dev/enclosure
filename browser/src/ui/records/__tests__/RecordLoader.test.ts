import { describe, expect, it } from "vitest";
import { sirenFixtures as fixtures } from "../../../stories/SirenFixtures";
import { RecordLoader } from "../RecordLoader";

class ExampleDocuments {
  page(
    content: string,
    offset: number,
    total: number,
    next: string = "",
    revision: string = "example-revision",
  ) {
    return fixtures.entity(
      ["command-result"],
      "Example source",
      {
        record_id: "example-record",
        revision,
        content,
        offset,
        total_characters: total,
        has_more: next !== "",
        next_offset: offset + Array.from(content).length,
      },
      next ? [fixtures.link(next, ["next"], "Next page")] : [],
      [],
      [],
    );
  }
}
const documents = new ExampleDocuments();
const identity = { record_id: "example-record" };

describe("revision-pinned record documents", () => {
  it("reassembles Unicode source using server character offsets", async () => {
    const pages = [
      documents.page("🌍", 0, 3, "/example-next"),
      documents.page("é!", 1, 3),
    ];
    const loader = new RecordLoader(async () => {
      const page = pages.shift();
      if (!page) throw new Error("Unexpected example request");
      return page;
    });
    await expect(
      loader.text("/example-start", "example-revision", identity),
    ).resolves.toBe("🌍é!");
  });

  it.each([
    ["changed revision", documents.page("abc", 0, 3, "", "example-other")],
    ["missing first characters", documents.page("abc", 1, 4)],
    ["truncated final page", documents.page("ab", 0, 3)],
    ["empty continuation", documents.page("", 0, 3, "/example-next")],
  ])("rejects %s before a complete source can be saved", async (_, page) => {
    const loader = new RecordLoader(async () => page);
    await expect(
      loader.text("/example-start", "example-revision", identity),
    ).rejects.toThrow();
  });

  it("rejects a continuation loop instead of loading indefinitely", async () => {
    const loader = new RecordLoader(async () =>
      documents.page("a", 0, 2, "/example-start"),
    );
    await expect(
      loader.text("/example-start", "example-revision", identity),
    ).rejects.toThrow("repeated continuation");
  });

  it("rejects content belonging to a different resource", async () => {
    const loader = new RecordLoader(async () => documents.page("abc", 0, 3));
    await expect(
      loader.text("/example-start", "example-revision", {
        record_id: "example-other",
      }),
    ).rejects.toThrow("changed or returned an incomplete page");
  });
});
