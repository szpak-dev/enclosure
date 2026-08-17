import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

function trimOutputWhitespace(): Plugin {
  return {
    name: "trim-output-whitespace",
    enforce: "post",
    generateBundle(_, bundle) {
      for (const file of Object.values(bundle)) {
        if (file.type === "chunk") {
          file.code = file.code.replace(/[ \t]+$/gm, "");
        }
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), trimOutputWhitespace()],
  base: "/static/browser/",
  resolve: {
    alias: {
      "dayjs/plugin/customParseFormat": "dayjs/plugin/customParseFormat.js",
    },
  },
  build: {
    outDir: resolve(
      import.meta.dirname,
      "../src/enclosure/browser/adapters/http/static/browser",
    ),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        assetFileNames: "browser.[ext]",
        codeSplitting: false,
        entryFileNames: "browser.js",
      },
    },
  },
  test: {
    environment: "jsdom",
    server: {
      deps: {
        inline: ["@rjsf/mantine"],
      },
    },
    setupFiles: "./src/test/setup.ts",
  },
});
