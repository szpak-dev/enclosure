import {
  ActionIcon,
  Alert,
  Button,
  Popover,
  Stack,
  Text,
  VisuallyHidden,
} from "@mantine/core";
import type { Entity, Target } from "@siren-js/client";
import { IconDownload } from "@tabler/icons-react";
import { Component, type ReactNode } from "react";

type DiagramPngFile = {
  filename: string;
  content: Uint8Array<ArrayBuffer>;
};

type DiagramDownloadProps = {
  diagramId: string;
  revision: number;
  title: string;
  onLoad: (target: Target) => Promise<Entity>;
} & (
  | { presentation: "button"; source: string; entity: Entity }
  | {
      presentation: "icon";
      target: Target;
    }
);

type DownloadState =
  | { status: "idle" }
  | { status: "rendering" }
  | { status: "error"; message: string };

class DiagramDownloadControl extends Component<
  DiagramDownloadProps,
  DownloadState
> {
  state: DownloadState = { status: "idle" };
  private generation: number = 0;
  private busy: boolean = false;

  componentDidUpdate(previous: DiagramDownloadProps): void {
    if (
      previous.diagramId !== this.props.diagramId ||
      previous.revision !== this.props.revision ||
      previous.presentation !== this.props.presentation ||
      (previous.presentation === "button" &&
        this.props.presentation === "button" &&
        previous.source !== this.props.source) ||
      (previous.presentation === "icon" &&
        this.props.presentation === "icon" &&
        previous.target !== this.props.target)
    ) {
      this.generation += 1;
      this.busy = false;
      this.setState({ status: "idle" });
    }
  }

  componentWillUnmount(): void {
    this.generation += 1;
  }

  async readFile(): Promise<DiagramPngFile> {
    const entity =
      this.props.presentation === "button"
        ? this.props.entity
        : await this.props.onLoad(this.props.target);
    const download = entity.links.find((link) =>
      link.rel.includes("enclosure:download-png"),
    );
    if (!download) {
      throw new Error("PNG download is unavailable for this diagram.");
    }
    const result = await this.props.onLoad(download);
    const properties = result.properties;
    if (
      !("diagram_id" in properties) ||
      properties.diagram_id !== this.props.diagramId ||
      !("revision" in properties) ||
      properties.revision !== this.props.revision ||
      !("filename" in properties) ||
      typeof properties.filename !== "string" ||
      !("media_type" in properties) ||
      properties.media_type !== "image/png" ||
      !("content" in properties) ||
      typeof properties.content !== "string" ||
      !properties.content.trim() ||
      !("content_revision" in properties) ||
      typeof properties.content_revision !== "string" ||
      !("total_bytes" in properties) ||
      typeof properties.total_bytes !== "number" ||
      !("width" in properties) ||
      typeof properties.width !== "number" ||
      !("height" in properties) ||
      typeof properties.height !== "number"
    ) {
      throw new Error(
        "The PNG response does not contain a complete matching image.",
      );
    }
    const content = Uint8Array.from(atob(properties.content), (character) =>
      character.charCodeAt(0),
    );
    const header = new DataView(content.buffer);
    if (
      content.length !== properties.total_bytes ||
      content.length < 24 ||
      header.getUint32(0) !== 0x89504e47 ||
      header.getUint32(4) !== 0x0d0a1a0a ||
      header.getUint32(16) !== properties.width ||
      header.getUint32(20) !== properties.height ||
      properties.width <= 0 ||
      properties.height <= 0
    ) {
      throw new Error(
        "The PNG response does not contain a complete matching image.",
      );
    }
    const digest = await crypto.subtle.digest("SHA-256", content);
    const revision = Array.from(new Uint8Array(digest), (byte) =>
      byte.toString(16).padStart(2, "0"),
    ).join("");
    if (revision !== properties.content_revision) {
      throw new Error(
        "The PNG document failed its integrity check. Try downloading again.",
      );
    }
    return { filename: properties.filename, content };
  }

  download = async (): Promise<void> => {
    if (this.busy) return;

    this.busy = true;
    const generation = ++this.generation;
    this.setState({ status: "rendering" });

    try {
      const artifact = await this.readFile();
      if (generation !== this.generation) return;

      const file = new Blob([artifact.content], {
        type: "image/png",
      });
      const url = URL.createObjectURL(file);
      const link = document.createElement("a");
      link.href = url;
      link.download = artifact.filename;
      try {
        document.body.append(link);
        link.click();
      } finally {
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
      this.busy = false;
      this.setState({ status: "idle" });
    } catch (error: unknown) {
      if (generation !== this.generation) return;

      this.busy = false;
      this.setState({
        status: "error",
        message:
          error instanceof Error
            ? error.message
            : "The diagram could not be downloaded.",
      });
    }
  };

  render(): ReactNode {
    if (this.props.presentation === "icon") {
      return (
        <Popover
          opened={this.state.status === "error"}
          onClose={() => this.setState({ status: "idle" })}
          position="bottom-end"
          width={280}
          withArrow
        >
          <Popover.Target>
            <ActionIcon
              aria-label={`Download ${this.props.title} as PNG`}
              title={`Download ${this.props.title} as PNG`}
              loading={this.state.status === "rendering"}
              onClick={this.download}
              size="lg"
              variant="subtle"
            >
              <IconDownload aria-hidden size={20} />
            </ActionIcon>
          </Popover.Target>
          {this.state.status === "rendering" ? (
            <VisuallyHidden role="status">
              Preparing {this.props.title} PNG…
            </VisuallyHidden>
          ) : null}
          <Popover.Dropdown>
            {this.state.status === "error" ? (
              <Alert color="red" role="alert" title="Unable to download PNG">
                <Stack gap="xs">
                  <Text size="sm">{this.state.message}</Text>
                  <Button onClick={this.download} size="xs" variant="light">
                    Retry download
                  </Button>
                </Stack>
              </Alert>
            ) : null}
          </Popover.Dropdown>
        </Popover>
      );
    }

    return (
      <Stack gap="xs" align="start">
        <Button
          disabled={
            !this.props.source.trim() ||
            !this.props.entity.links.some((link) =>
              link.rel.includes("enclosure:download-png"),
            )
          }
          leftSection={<IconDownload aria-hidden size={18} />}
          loading={this.state.status === "rendering"}
          onClick={this.download}
          variant="default"
        >
          Download PNG
        </Button>
        {this.state.status === "rendering" ? (
          <Text role="status" size="sm">
            Preparing PNG…
          </Text>
        ) : null}
        {this.state.status === "error" ? (
          <Alert color="red" role="alert" title="Unable to download PNG">
            {this.state.message} Try Download PNG again to retry.
          </Alert>
        ) : null}
      </Stack>
    );
  }
}

export function DiagramDownload(props: DiagramDownloadProps): ReactNode {
  return <DiagramDownloadControl {...props} />;
}
