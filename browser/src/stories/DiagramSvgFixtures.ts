import { sirenFixtures } from "./SirenFixtures";

export class DiagramSvgFixtures {
  link(id = "example", revision = 1) {
    return sirenFixtures.link(
      `/example-exports/${id}?expected_revision=${revision}`,
      ["enclosure:download-svg"],
      "Download diagram SVG",
    );
  }

  async document(id = "example", revision = 1) {
    const content =
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><text x="0" y="20">Example zażółć 🐈</text></svg>';
    const hash = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(content),
    );
    return sirenFixtures.entity(
      ["diagram-svg"],
      "Example SVG",
      {
        diagram_id: id,
        revision,
        filename: `diagram-${id}-r${revision}.svg`,
        media_type: "image/svg+xml",
        content,
        content_revision: Array.from(new Uint8Array(hash), (byte) =>
          byte.toString(16).padStart(2, "0"),
        ).join(""),
        offset: 0,
        limit: Array.from(content).length,
        total_characters: Array.from(content).length,
        has_more: false,
        next_offset: Array.from(content).length,
      },
      [],
      [],
      [],
    );
  }
}

export const diagramSvgFixtures = new DiagramSvgFixtures();
