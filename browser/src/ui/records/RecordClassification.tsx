import {
  Accordion,
  Alert,
  Badge,
  Button,
  Group,
  List,
  Skeleton,
  Stack,
  Text,
} from "@mantine/core";
import { Component, type ReactNode } from "react";
import {
  Identity,
  ResourcePage,
  Section,
} from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenContinuation } from "../siren/SirenContinuation";
import { recordContract as contract, type JsonObject } from "./RecordContract";
import { RecordActions } from "./RecordActions";
import { RecordBoundary, RecordContent, RecordLink } from "./RecordPrimitives";
import { RecordLoader } from "./RecordLoader";

function ClassificationCollectionView(props: SirenEntityProps): ReactNode {
  const category = props.entity.class.includes("category");
  const kind = category ? "categories" : "tags";
  const title = category ? "Categories" : "Tags";
  return (
    <ResourcePage
      title={title}
      description={
        category
          ? "Content schemas used to classify and validate records."
          : "Reusable labels for classifying records."
      }
    >
      <Group justify="flex-end">
        <RecordActions
          actions={props.entity.actions.filter(
            (action) =>
              action.name ===
              (category ? "create_record_category" : "create_record_tag"),
          )}
          values={{}}
          primary={category ? "create_record_category" : "create_record_tag"}
          root={props.root}
          onFollow={props.onFollow}
          onRefresh={props.onRefresh}
          danger={false}
          collection={kind}
        />
      </Group>
      {props.entity.entities.length ? (
        <List
          listStyleType="none"
          spacing="md"
          styles={{
            itemWrapper: { width: "100%" },
            itemLabel: { width: "100%" },
          }}
        >
          {props.entity.entities.map((item) => {
            const data = contract.object(contract.properties(item));
            const id = contract.string(data.id);
            const label = contract.string(category ? data.title : data.name);
            const target = contract.target(item);
            return (
              <List.Item key={id}>
                <Group justify="space-between" wrap="nowrap" w="100%">
                  <Stack gap={4} miw={0}>
                    {target.kind === "available" ? (
                      <RecordLink
                        target={target.value}
                        onFollow={props.onFollow}
                      >
                        {label}
                      </RecordLink>
                    ) : (
                      <Text>{label}</Text>
                    )}
                    {category ? (
                      <Badge variant="light">
                        Schema v{contract.number(data.schema_version)}
                      </Badge>
                    ) : (
                      <></>
                    )}
                  </Stack>
                  {target.kind === "available" ? (
                    <Button
                      variant="light"
                      aria-label={`Open ${label}`}
                      onClick={() => props.onFollow(target.value)}
                    >
                      Open
                    </Button>
                  ) : (
                    <Text>Navigation unavailable</Text>
                  )}
                </Group>
              </List.Item>
            );
          })}
        </List>
      ) : (
        <Alert title={`No ${kind} yet`}>
          Create{" "}
          {category
            ? "a category to define a record content schema"
            : "a tag to classify records"}
          .
        </Alert>
      )}
      <SirenContinuation entity={props.entity} onFollow={props.onFollow} />
    </ResourcePage>
  );
}

export function RecordClassificationCollection(
  props: SirenEntityProps,
): ReactNode {
  return (
    <RecordBoundary entity={props.entity} onRefresh={props.onRefresh}>
      <ClassificationCollectionView {...props} />
    </RecordBoundary>
  );
}

type SchemaLoad =
  | { kind: "loading" }
  | { kind: "failed"; message: string }
  | { kind: "ready"; value: JsonObject };

class CategoryDetailView extends Component<SirenEntityProps, SchemaLoad> {
  state: SchemaLoad = { kind: "loading" };
  private generation = 0;
  componentDidMount(): void {
    void this.load();
  }
  componentWillUnmount(): void {
    this.generation += 1;
  }
  componentDidUpdate(previous: SirenEntityProps): void {
    if (previous.entity !== this.props.entity) void this.load();
  }
  private async load(): Promise<void> {
    const generation = ++this.generation;
    this.setState({ kind: "loading" });
    try {
      const data = contract.object(this.props.entity.properties);
      const revision = contract.string(data.content_schema_revision);
      const action = contract.required(
        contract.action(
          this.props.entity,
          "read_record_category_content_schema",
        ),
        "Schema inspection is unavailable.",
      );
      const source = await new RecordLoader(this.props.onLoad).text(
        contract.query(action, {
          expected_revision: revision,
          schema_version: contract.number(data.schema_version),
          offset: 0,
          limit: 10000,
        }),
        revision,
        {
          category_id: contract.string(data.id),
          schema_version: contract.number(data.schema_version),
        },
      );
      const value = contract.parseContent(source);
      if (generation === this.generation)
        this.setState({ kind: "ready", value });
    } catch (reason) {
      if (generation === this.generation)
        this.setState({ kind: "failed", message: contract.message(reason) });
    }
  }

  render(): ReactNode {
    const data = contract.object(this.props.entity.properties);
    const actions = this.props.entity.actions.filter(
      (action) =>
        action.name === "update_record_category" ||
        (this.state.kind === "ready" &&
          action.name === "update_record_category_content_schema"),
    );
    const values =
      this.state.kind === "ready"
        ? { ...data, content_schema: this.state.value }
        : data;
    return (
      <ResourcePage
        title={contract.string(data.title)}
        description="Record category and its current content schema."
      >
        <Badge>Schema v{contract.number(data.schema_version)}</Badge>
        <RecordActions
          actions={actions}
          values={values}
          primary="update_record_category"
          root={this.props.root}
          onFollow={this.props.onFollow}
          onRefresh={this.props.onRefresh}
          danger={false}
          collection="categories"
        />
        <Alert title="Versioned schema">
          Updating a referenced schema publishes a new version. Existing records
          retain their assigned version.
        </Alert>
        <Section title="Content schema">
          {this.state.kind === "loading" ? (
            <Skeleton
              height={100}
              role="status"
              aria-label="Loading content schema"
            />
          ) : this.state.kind === "failed" ? (
            <Alert color="red" title="Schema unavailable">
              <Stack>
                {this.state.message}
                <Button onClick={() => void this.load()}>Retry schema</Button>
              </Stack>
            </Alert>
          ) : (
            <RecordContent value={this.state.value} />
          )}
        </Section>
        <Accordion>
          <Accordion.Item value="technical">
            <Accordion.Control>Technical details</Accordion.Control>
            <Accordion.Panel>
              <Stack>
                <Identity
                  label="Category ID"
                  value={contract.string(data.id)}
                />
                <Identity
                  label="Schema revision"
                  value={contract.string(data.content_schema_revision)}
                />
              </Stack>
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>
        <RecordActions
          actions={this.props.entity.actions.filter(
            (action) => action.name === "delete_record_category",
          )}
          values={data}
          primary=""
          root={this.props.root}
          onFollow={this.props.onFollow}
          onRefresh={this.props.onRefresh}
          danger
          collection="categories"
        />
      </ResourcePage>
    );
  }
}

function TagDetailView(props: SirenEntityProps): ReactNode {
  const tag = contract.tag(props.entity.properties);
  return (
    <ResourcePage title={tag.name} description="Record classification tag.">
      <RecordActions
        actions={props.entity.actions.filter(
          (action) => action.name === "update_record_tag",
        )}
        values={{ name: tag.name }}
        primary="update_record_tag"
        root={props.root}
        onFollow={props.onFollow}
        onRefresh={props.onRefresh}
        danger={false}
        collection="tags"
      />
      <Identity label="Tag ID" value={tag.id} />
      <RecordActions
        actions={props.entity.actions.filter(
          (action) => action.name === "delete_record_tag",
        )}
        values={{ name: tag.name }}
        primary=""
        root={props.root}
        onFollow={props.onFollow}
        onRefresh={props.onRefresh}
        danger
        collection="tags"
      />
    </ResourcePage>
  );
}

export function RecordCategoryDetail(props: SirenEntityProps): ReactNode {
  return (
    <RecordBoundary entity={props.entity} onRefresh={props.onRefresh}>
      <CategoryDetailView {...props} />
    </RecordBoundary>
  );
}
export function RecordTagDetail(props: SirenEntityProps): ReactNode {
  return (
    <RecordBoundary entity={props.entity} onRefresh={props.onRefresh}>
      <TagDetailView {...props} />
    </RecordBoundary>
  );
}
