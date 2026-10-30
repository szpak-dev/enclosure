import { Alert, Button, Group, Loader, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import type { Action, Entity, Target } from "@siren-js/client";
import { Component, type ReactNode } from "react";
import { ResourcePage } from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenContinuation } from "../siren/SirenContinuation";
import {
  useSirenActionExecution,
  type SirenActionExecutor,
} from "../siren/SirenActionExecution";
import { recordContract as contract, type Available } from "./RecordContract";
import { RecordBoundary, RecordRows } from "./RecordPrimitives";
import { RecordEditor } from "./RecordEditor";

type EditorSelection =
  | { kind: "closed" }
  | { kind: "open"; action: Action; source: Available<Target> };
type SearchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "failed"; message: string }
  | { kind: "ready"; entity: Entity; query: string };
type CollectionState = {
  query: string;
  search: SearchState;
  editor: EditorSelection;
};
type CollectionProps = SirenEntityProps & {
  execute: Available<SirenActionExecutor>;
};

class RecordCollectionView extends Component<CollectionProps, CollectionState> {
  state: CollectionState = {
    query: "",
    search: { kind: "idle" },
    editor: { kind: "closed" },
  };
  private generation = 0;
  componentWillUnmount(): void {
    this.generation += 1;
  }
  componentDidUpdate(previous: CollectionProps): void {
    if (previous.entity !== this.props.entity) {
      this.generation += 1;
      this.setState({
        search: { kind: "idle" },
      });
    }
  }

  private async search(): Promise<void> {
    const action = contract.action(this.props.root, "search_records");
    const execute = this.props.execute;
    if (
      action.kind === "unavailable" ||
      execute.kind === "unavailable" ||
      !this.state.query.trim()
    )
      return;
    const query = this.state.query.trim();
    const generation = ++this.generation;
    this.setState({ search: { kind: "loading" } });
    try {
      const result = await execute.value(action.value, { query, limit: 50 });
      if (result.kind !== "entity")
        throw new Error("The search did not return a result document.");
      if (generation === this.generation)
        this.setState({
          search: { kind: "ready", entity: result.entity, query },
        });
    } catch (reason) {
      if (generation === this.generation)
        this.setState({
          search: { kind: "failed", message: contract.message(reason) },
        });
    }
  }

  render(): ReactNode {
    const localCreate = contract.action(this.props.entity, "create_record");
    const create =
      localCreate.kind === "available"
        ? localCreate
        : contract.action(this.props.root, "create_record");
    const search = contract.action(this.props.root, "search_records");
    const state = this.state.search;
    const entity = state.kind === "ready" ? state.entity : this.props.entity;
    const searching =
      state.kind !== "idle" ||
      this.props.entity.class.includes("search-result");
    return (
      <ResourcePage
        title="Records"
        description="Categorized knowledge and its source resources."
      >
        <Group justify="flex-end">
          {create.kind === "available" ? (
            <Button
              onClick={() =>
                this.setState({
                  editor: {
                    kind: "open",
                    action: create.value,
                    source: { kind: "unavailable" },
                  },
                })
              }
            >
              New record
            </Button>
          ) : (
            <></>
          )}
        </Group>
        {search.kind === "available" &&
        this.props.execute.kind === "available" ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void this.search();
            }}
          >
            <Group align="flex-end">
              <TextInput
                flex={1}
                miw={180}
                label="Describe what you’re looking for"
                placeholder="Search records by meaning"
                value={this.state.query}
                onChange={(event) =>
                  this.setState({ query: event.currentTarget.value })
                }
              />
              <Button
                type="submit"
                loading={state.kind === "loading"}
                disabled={!this.state.query.trim()}
              >
                Search
              </Button>
              {state.kind !== "idle" ||
              this.state.query ||
              this.props.entity.class.includes("search-result") ? (
                <Button
                  variant="default"
                  onClick={() => {
                    this.generation += 1;
                    this.setState({ query: "", search: { kind: "idle" } });
                    if (this.props.entity.class.includes("search-result")) {
                      const collection = contract.collection(
                        this.props.root,
                        "records",
                      );
                      if (collection.kind === "available")
                        this.props.onFollow(collection.value);
                    }
                  }}
                >
                  Clear search
                </Button>
              ) : (
                <></>
              )}
            </Group>
          </form>
        ) : (
          <></>
        )}
        {state.kind === "loading" ? (
          <Loader aria-label="Searching records" role="status" />
        ) : state.kind === "failed" ? (
          <Alert color="red" role="alert" title="Search unavailable">
            <Stack>
              {state.message}
              <Button onClick={() => void this.search()}>Retry search</Button>
            </Stack>
          </Alert>
        ) : (
          <>
            {state.kind === "ready" ? (
              <Alert title={`Results for “${state.query}”`}>
                Showing up to 50 semantic matches.
              </Alert>
            ) : (
              <></>
            )}
            {entity.entities.length ? (
              <RecordRows
                items={entity.entities}
                onFollow={this.props.onFollow}
                onEdit={(action, target) =>
                  this.setState({
                    editor: {
                      kind: "open",
                      action,
                      source: { kind: "available", value: target },
                    },
                  })
                }
              />
            ) : (
              <Alert
                title={searching ? "No matching records" : "No records yet"}
              >
                {searching
                  ? "Try a different description or clear the search."
                  : "Create a record to add categorized knowledge and source resources."}
              </Alert>
            )}
            <SirenContinuation entity={entity} onFollow={this.props.onFollow} />
          </>
        )}
        {this.state.editor.kind === "open" ? (
          <RecordEditor
            action={this.state.editor.action}
            source={this.state.editor.source}
            root={this.props.root}
            onLoad={this.props.onLoad}
            onClose={() => this.setState({ editor: { kind: "closed" } })}
            onSaved={(saved) => {
              const target = contract.required(
                contract.target(saved),
                "The saved record does not advertise its detail page.",
              );
              this.setState({ editor: { kind: "closed" } });
              notifications.show({
                title: "Record saved",
                message: "Your record and attachments have been saved.",
                color: "teal",
              });
              this.props.onFollow(target);
            }}
          />
        ) : (
          <></>
        )}
      </ResourcePage>
    );
  }
}

export function RecordCollection(props: SirenEntityProps): ReactNode {
  const execution = useSirenActionExecution();
  return (
    <RecordBoundary entity={props.entity} onRefresh={props.onRefresh}>
      <RecordCollectionView
        {...props}
        execute={
          execution.kind === "available"
            ? { kind: "available", value: execution.execute }
            : { kind: "unavailable" }
        }
      />
    </RecordBoundary>
  );
}
