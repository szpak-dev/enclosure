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

type DiagramSvgFile = {
  filename: string;
  content: string;
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

  async readFile(): Promise<DiagramSvgFile> {
    const entity =
      this.props.presentation === "button"
        ? this.props.entity
        : await this.props.onLoad(this.props.target);
    const download = entity.links.find((link) =>
      link.rel.includes("enclosure:download-svg"),
    );
    if (!download) {
      throw new Error("SVG download is unavailable for this diagram.");
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
      properties.media_type !== "image/svg+xml" ||
      !("content" in properties) ||
      typeof properties.content !== "string" ||
      !properties.content.trim() ||
      !("content_revision" in properties) ||
      typeof properties.content_revision !== "string" ||
      !("offset" in properties) ||
      properties.offset !== 0 ||
      !("total_characters" in properties) ||
      properties.total_characters !== Array.from(properties.content).length ||
      !("has_more" in properties) ||
      properties.has_more !== false
    ) {
      throw new Error(
        "The SVG response does not contain a complete matching document.",
      );
    }
    const digest = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(properties.content),
    );
    const revision = Array.from(new Uint8Array(digest), (byte) =>
      byte.toString(16).padStart(2, "0"),
    ).join("");
    if (revision !== properties.content_revision) {
      throw new Error(
        "The SVG document failed its integrity check. Try downloading again.",
      );
    }
    return { filename: properties.filename, content: properties.content };
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
        type: "image/svg+xml;charset=utf-8",
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
              aria-label={`Download ${this.props.title} as SVG`}
              title={`Download ${this.props.title} as SVG`}
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
              Preparing {this.props.title} SVG…
            </VisuallyHidden>
          ) : null}
          <Popover.Dropdown>
            {this.state.status === "error" ? (
              <Alert color="red" role="alert" title="Unable to download SVG">
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
              link.rel.includes("enclosure:download-svg"),
            )
          }
          leftSection={<IconDownload aria-hidden size={18} />}
          loading={this.state.status === "rendering"}
          onClick={this.download}
          variant="default"
        >
          Download SVG
        </Button>
        {this.state.status === "rendering" ? (
          <Text role="status" size="sm">
            Preparing SVG…
          </Text>
        ) : null}
        {this.state.status === "error" ? (
          <Alert color="red" role="alert" title="Unable to download SVG">
            {this.state.message} Try Download SVG again to retry.
          </Alert>
        ) : null}
      </Stack>
    );
  }
}

export function DiagramDownload(props: DiagramDownloadProps): ReactNode {
  return <DiagramDownloadControl {...props} />;
}
