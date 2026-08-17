import { Alert } from "@mantine/core";
import { Component, type ReactNode } from "react";

export type DiagramPreviewErrorBoundaryProps = {
  children: ReactNode;
};

type DiagramPreviewErrorBoundaryState = {
  error: Error | null;
};

export class DiagramPreviewErrorBoundary extends Component<
  DiagramPreviewErrorBoundaryProps,
  DiagramPreviewErrorBoundaryState
> {
  state: DiagramPreviewErrorBoundaryState = { error: null };

  static getDerivedStateFromError(
    error: Error,
  ): DiagramPreviewErrorBoundaryState {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <Alert
          color="red"
          role="alert"
          title="Unable to render diagram preview"
        >
          {this.state.error.message}
        </Alert>
      );
    }

    return this.props.children;
  }
}
