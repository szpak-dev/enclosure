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
import { MermaidRenderer, type MermaidTheme } from "./MermaidRenderer";

type DiagramDownloadSource = {
  diagramId: string;
  revision: number;
  source: string;
};

type DiagramDownloadProps = {
  diagramId: string;
  revision: number;
  theme: MermaidTheme;
  title: string;
} & (
  | { presentation: "button"; source: string }
  | {
      presentation: "icon";
      target: Target;
      onLoad: (target: Target) => Promise<Entity>;
    }
);

type DownloadState =
  | { status: "idle" }
  | { status: "rendering" }
  | { status: "error"; message: string };

export class DiagramDownload extends Component<
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
      previous.theme !== this.props.theme ||
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

  async readSource(): Promise<DiagramDownloadSource> {
    if (this.props.presentation === "button") {
      return {
        diagramId: this.props.diagramId,
        revision: this.props.revision,
        source: this.props.source,
      };
    }

    const entity = await this.props.onLoad(this.props.target);
    const properties = entity.properties;
    if (
      !("id" in properties) ||
      typeof properties.id !== "string" ||
      !("revision" in properties) ||
      typeof properties.revision !== "number" ||
      !("source" in properties) ||
      typeof properties.source !== "string"
    ) {
      throw new Error(
        "The diagram response does not contain SVG rendering data.",
      );
    }
    return {
      diagramId: properties.id,
      revision: properties.revision,
      source: properties.source,
    };
  }

  download = async (): Promise<void> => {
    if (this.busy) return;

    this.busy = true;
    const generation = ++this.generation;
    const { theme } = this.props;
    this.setState({ status: "rendering" });

    try {
      const { diagramId, revision, source } = await this.readSource();
      if (generation !== this.generation) return;
      if (!source.trim()) throw new Error("Diagram has no source.");
      const renderer = new MermaidRenderer(theme);
      const rendering = await renderer.render(
        source,
        `download-${crypto.randomUUID()}`,
      );
      if (generation !== this.generation) return;

      const file = new Blob([rendering.svg], {
        type: "image/svg+xml;charset=utf-8",
      });
      const url = URL.createObjectURL(file);
      const link = document.createElement("a");
      link.href = url;
      link.download = `diagram-${diagramId}-r${revision}.svg`;
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
          disabled={!this.props.source.trim()}
          leftSection={<IconDownload aria-hidden size={18} />}
          loading={this.state.status === "rendering"}
          onClick={this.download}
          variant="default"
        >
          Download SVG
        </Button>
        {this.state.status === "rendering" ? (
          <Text role="status" size="sm">
            Rendering SVG…
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
