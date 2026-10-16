import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { once } from "node:events";
import { setTimeout as pause } from "node:timers/promises";

const EXPECTED_COMPONENTS = [
  "browser-application",
  "browser-siren-collection",
  "browser-siren-entity",
  "browser-siren-page",
];
const REQUIRED_MCP_TOOLS = [
  "docs-list",
  "docs-show",
  "stories-preview",
  "test-run",
];

class StorybookContractVerifier {
  constructor(port = 6106) {
    this.port = port;
    this.origin = `http://127.0.0.1:${port}`;
    this.server = undefined;
    this.serverOutput = "";
  }

  async run() {
    const staticStoryIds = await this.verifyStaticBuild();

    try {
      await this.startServer();
      await this.waitUntilReady();
      await this.verifyLiveManifest(staticStoryIds);
      await this.verifyMcp(staticStoryIds);
    } finally {
      await this.stopServer();
    }

    console.log(
      `Storybook contract verified for ${staticStoryIds.size} authoritative stories.`,
    );
  }

  async verifyStaticBuild() {
    const index = JSON.parse(
      await readFile(
        new URL("../storybook-static/index.json", import.meta.url),
      ),
    );
    const manifest = JSON.parse(
      await readFile(
        new URL(
          "../storybook-static/manifests/components.json",
          import.meta.url,
        ),
      ),
    );
    const storyIds = new Set(
      Object.values(index.entries)
        .filter((entry) => entry.type === "story")
        .map((entry) => entry.id),
    );

    this.verifyManifest(manifest, storyIds, "static");
    return storyIds;
  }

  verifyManifest(manifest, storyIds, source) {
    for (const componentId of EXPECTED_COMPONENTS) {
      const component = manifest.components?.[componentId];
      if (!component || component.stories.length === 0) {
        throw new Error(
          `The ${source} component manifest does not expose ${componentId}.`,
        );
      }

      for (const story of component.stories) {
        if (!storyIds.has(story.id)) {
          throw new Error(
            `The ${source} component manifest advertises missing story ${story.id}.`,
          );
        }
      }
    }
  }

  async startServer() {
    this.server = spawn(
      process.platform === "win32"
        ? "node_modules/.bin/storybook.cmd"
        : "node_modules/.bin/storybook",
      [
        "dev",
        "--ci",
        "--no-open",
        "--host",
        "127.0.0.1",
        "--port",
        `${this.port}`,
      ],
      {
        cwd: new URL("..", import.meta.url),
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    const recordOutput = (chunk) => {
      this.serverOutput = `${this.serverOutput}${chunk}`.slice(-20_000);
    };
    this.server.stdout.on("data", recordOutput);
    this.server.stderr.on("data", recordOutput);
  }

  async waitUntilReady() {
    const deadline = Date.now() + 90_000;
    const manifestUrl = `${this.origin}/manifests/components.json`;

    while (Date.now() < deadline) {
      if (this.server.exitCode !== null) {
        throw new Error(
          `Storybook exited before it became ready.\n${this.serverOutput}`,
        );
      }

      try {
        const response = await fetch(manifestUrl);
        if (response.ok) {
          return;
        }
      } catch {
        // The development server has not started listening yet.
      }
      await pause(250);
    }

    throw new Error(`Storybook did not become ready.\n${this.serverOutput}`);
  }

  async verifyLiveManifest(staticStoryIds) {
    const response = await fetch(`${this.origin}/manifests/components.json`);
    if (!response.ok) {
      throw new Error(
        `Unable to read the live component manifest: ${response.status}.`,
      );
    }
    this.verifyManifest(await response.json(), staticStoryIds, "live");
  }

  async verifyMcp(storyIds) {
    const initialized = await this.mcpRequest("initialize", {
      capabilities: {},
      clientInfo: { name: "enclosure-storybook-contract", version: "1.0.0" },
      protocolVersion: "2025-06-18",
    });
    const sessionId = initialized.sessionId;
    if (!sessionId) {
      throw new Error("Storybook MCP did not establish a session.");
    }

    await this.mcpNotification("notifications/initialized", sessionId);
    const listed = await this.mcpRequest("tools/list", {}, sessionId);
    const toolNames = new Set(
      listed.message.result.tools.map((tool) => tool.name),
    );
    for (const toolName of REQUIRED_MCP_TOOLS) {
      if (!toolNames.has(toolName)) {
        throw new Error(`Storybook MCP does not expose ${toolName}.`);
      }
    }

    const documentation = await this.mcpRequest(
      "tools/call",
      { arguments: { withStoryIds: true }, name: "docs-list" },
      sessionId,
    );
    const documentationText = documentation.message.result.content
      .filter((item) => item.type === "text")
      .map((item) => item.text)
      .join("\n");
    for (const componentId of EXPECTED_COMPONENTS) {
      const componentStoryIds = [...storyIds].filter((storyId) =>
        storyId.startsWith(`${componentId}--`),
      );
      if (
        !componentStoryIds.some((storyId) =>
          documentationText.includes(storyId),
        )
      ) {
        throw new Error(
          `Storybook MCP documentation does not expose stories for ${componentId}.`,
        );
      }
    }
  }

  async mcpRequest(method, params, sessionId) {
    const headers = {
      Accept: "application/json, text/event-stream",
      "Content-Type": "application/json",
    };
    if (sessionId) {
      headers["Mcp-Session-Id"] = sessionId;
    }
    const response = await fetch(`${this.origin}/mcp`, {
      body: JSON.stringify({ id: 1, jsonrpc: "2.0", method, params }),
      headers,
      method: "POST",
      signal: AbortSignal.timeout(30_000),
    });
    const body = await response.text();
    if (!response.ok) {
      throw new Error(
        `Storybook MCP ${method} failed: ${response.status} ${body}`,
      );
    }
    const message = this.parseMcpMessage(body);
    if (message.error) {
      throw new Error(
        `Storybook MCP ${method} failed: ${JSON.stringify(message.error)}`,
      );
    }
    return { message, sessionId: response.headers.get("mcp-session-id") };
  }

  async mcpNotification(method, sessionId) {
    const response = await fetch(`${this.origin}/mcp`, {
      body: JSON.stringify({ jsonrpc: "2.0", method }),
      headers: {
        Accept: "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Mcp-Session-Id": sessionId,
      },
      method: "POST",
      signal: AbortSignal.timeout(30_000),
    });
    if (!response.ok) {
      throw new Error(`Storybook MCP ${method} failed: ${response.status}.`);
    }
  }

  parseMcpMessage(body) {
    const data = body
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .find(Boolean);
    return JSON.parse(data ?? body);
  }

  async stopServer() {
    if (!this.server || this.server.exitCode !== null) {
      return;
    }
    this.server.kill("SIGTERM");
    await Promise.race([once(this.server, "exit"), pause(5_000)]);
    if (this.server.exitCode === null) {
      this.server.kill("SIGKILL");
      await once(this.server, "exit");
    }
  }
}

await new StorybookContractVerifier().run();
