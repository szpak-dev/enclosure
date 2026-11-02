import { Alert, Button, Stack } from "@mantine/core";
import type { Action, Entity, Target } from "@siren-js/client";
import { Component, type ReactNode } from "react";
import { SirenClient } from "../../client/SirenClient";
import { SirenActionExecutionProvider } from "../siren/SirenActionExecution";
import { SirenPage } from "../siren/SirenPage";
import { recordContract as contract } from "./RecordContract";
import { RecordEditor } from "./RecordEditor";

import { RecordsPreviewData } from "./RecordsPreviewData";
import type { PreviewProps } from "./RecordsPreviewTypes";

type PreviewSession = {
  entity: Entity;
  loading: boolean;
  error: string;
  editor: boolean;
};
export class RecordsPreview extends Component<PreviewProps, PreviewSession> {
  private readonly data = new RecordsPreviewData(this.props.scenario);
  private readonly client = new SirenClient();
  state: PreviewSession = {
    entity: this.data.initial(this.props.initial),
    loading: false,
    error: "",
    editor: this.props.initial === "editor" || this.props.initial === "new",
  };
  private readonly targets: Record<PreviewProps["initial"], string> = {
    records: "/siren/records",
    record: "/siren/records/example",
    editor: "/siren/records/example",
    new: "/siren/records",
    categories: "/siren/records/categories",
    category: "/siren/records/categories/example-notes",
    tags: "/siren/records/tags",
    tag: "/siren/records/tags/example-reference",
    resources: "/siren/records/example/resource-manifests",
    source: "/siren/records/example/resources/content",
  };
  private target: Target = this.targets[this.props.initial];
  private async follow(target: Target): Promise<void> {
    this.target = target;
    this.setState({ loading: true, error: "" });
    try {
      this.setState({ entity: await this.client.get(target), loading: false });
    } catch (reason) {
      this.setState({ error: contract.message(reason), loading: false });
    }
  }
  render(): ReactNode {
    return (
      <SirenActionExecutionProvider
        execute={async (action, values) => {
          const result = await this.client.execute(action, values);
          return result === null
            ? { kind: "empty" }
            : { kind: "entity", entity: result };
        }}
      >
        <Stack component="main" p="md">
          {this.state.error ? (
            <Alert color="red" title="Unable to load resource">
              <Stack>
                {this.state.error}
                <Button onClick={() => void this.follow(this.target)}>
                  Retry
                </Button>
              </Stack>
            </Alert>
          ) : (
            <SirenPage
              entity={this.state.entity}
              root={this.data.root()}
              isLoading={this.state.loading}
              onLoad={(target) => this.client.get(target)}
              onFollow={(target) => void this.follow(target)}
              onRefresh={() => void this.follow(this.target)}
              onSubmit={(action: Action, values: Record<string, unknown>) => {
                void this.client.execute(action, values).then((entity) => {
                  if (entity !== null) this.setState({ entity });
                });
              }}
            />
          )}
          {this.state.editor ? (
            <RecordEditor
              action={
                this.props.initial === "new"
                  ? this.data.create
                  : this.data.update
              }
              source={
                this.props.initial === "new"
                  ? { kind: "unavailable" }
                  : { kind: "available", value: "/siren/records/example" }
              }
              root={this.data.root()}
              onLoad={(target) => this.client.get(target)}
              onClose={() => this.setState({ editor: false })}
              onSaved={(entity) => this.setState({ entity, editor: false })}
            />
          ) : (
            <></>
          )}
        </Stack>
      </SirenActionExecutionProvider>
    );
  }
}
