import { sirenFixtures } from "./SirenFixtures";
import diagramImage from "./fixtures/example-diagram.png?inline";

export class DiagramPngFixtures {
  bytes(): Uint8Array<ArrayBuffer> {
    return Uint8Array.from(
      atob(diagramImage.slice(diagramImage.indexOf(",") + 1)),
      (character) => character.charCodeAt(0),
    );
  }

  read(file: Blob): Promise<Uint8Array> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () =>
        reader.result instanceof ArrayBuffer
          ? resolve(new Uint8Array(reader.result))
          : reject(new Error("Expected PNG bytes"));
      reader.onerror = () => reject(new Error("Cannot read PNG"));
      reader.readAsArrayBuffer(file);
    });
  }

  link(id = "example", revision = 1) {
    return sirenFixtures.link(
      `/example-exports/${id}?expected_revision=${revision}`,
      ["enclosure:download-png"],
      "Download diagram PNG",
    );
  }

  async document(id = "example", revision = 1) {
    const content = diagramImage.slice(diagramImage.indexOf(",") + 1);
    const bytes = this.bytes();
    const header = new DataView(bytes.buffer);
    const hash = await crypto.subtle.digest("SHA-256", bytes);
    return sirenFixtures.entity(
      ["diagram-png"],
      "Example PNG",
      {
        diagram_id: id,
        revision,
        filename: `diagram-${id}-r${revision}.png`,
        media_type: "image/png",
        content,
        content_revision: Array.from(new Uint8Array(hash), (byte) =>
          byte.toString(16).padStart(2, "0"),
        ).join(""),
        width: header.getUint32(16),
        height: header.getUint32(20),
        total_bytes: bytes.length,
      },
      [],
      [],
      [],
    );
  }
}

export const diagramPngFixtures = new DiagramPngFixtures();
