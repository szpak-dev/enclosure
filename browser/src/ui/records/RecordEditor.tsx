import {
  Accordion,
  Alert,
  Button,
  Drawer,
  Fieldset,
  Group,
  JsonInput,
  Modal,
  MultiSelect,
  Select,
  Skeleton,
  Stack,
  Text,
  Textarea,
  TextInput,
  SegmentedControl,
} from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import type { Action, Entity, Target } from "@siren-js/client";
import { Component, createRef, type ReactNode } from "react";
import { generateForm } from "@rjsf/mantine";
import type { IChangeEvent } from "@rjsf/core";
import type RjsfCoreForm from "@rjsf/core";
import {
  getUiOptions,
  titleId,
  type ArrayFieldTitleProps,
  type RJSFSchema,
} from "@rjsf/utils";
import { customizeValidator } from "@rjsf/validator-ajv8";
import Ajv2020 from "ajv/dist/2020";
import { Form } from "../form/Form";
import {
  useSirenActionExecution,
  type SirenActionExecutor,
} from "../siren/SirenActionExecution";
import {
  recordContract as contract,
  type Available,
  type JsonObject,
  type RecordDraft,
  type ResourceInput,
} from "./RecordContract";
import {
  RecordLoader,
  type ContentSchema,
  type PreparedRecord,
} from "./RecordLoader";

type SchemaState =
  | { kind: "unselected" }
  | { kind: "loading" }
  | { kind: "failed"; message: string }
  | { kind: "ready"; content: ContentSchema };
type Preparation =
  | { kind: "loading" }
  | { kind: "failed"; message: string }
  | { kind: "ready"; data: PreparedRecord };
type EditorState = {
  preparation: Preparation;
  schema: SchemaState;
  dirty: boolean;
  discard: boolean;
  saving: boolean;
  mode: string;
};
export type RecordEditorProps = {
  action: Action;
  source: Available<Target>;
  root: Entity;
  onLoad: (target: Target) => Promise<Entity>;
  onClose: () => void;
  onSaved: (entity: Entity) => void;
};
type SessionProps = RecordEditorProps & {
  narrow: boolean;
  execute: SirenActionExecutor;
};

export class RecordValidationError extends Error {
  constructor(readonly fieldErrors: Record<string, string>) {
    super("Please correct the highlighted fields.");
  }
}

class RecordArrayTitle extends Component<
  ArrayFieldTitleProps<JsonObject, RJSFSchema, Record<string, never>>
> {
  render(): ReactNode {
    const options = getUiOptions(
      this.props.uiSchema,
      this.props.registry.globalUiOptions,
    );
    return options.label === false ? (
      <></>
    ) : (
      <Group justify="space-between">
        <Text component="span" id={titleId(this.props.fieldPathId)} fw={600}>
          {this.props.title}
        </Text>
        {this.props.optionalDataControl}
      </Group>
    );
  }
}

class RecordFields extends Component<{
  errors: Record<string, string>;
  children: ReactNode;
}> {
  private readonly element = createRef<HTMLDivElement>();
  componentDidUpdate(
    previous: Readonly<{ errors: Record<string, string>; children: ReactNode }>,
  ): void {
    if (JSON.stringify(previous.errors) === JSON.stringify(this.props.errors))
      return;
    const element = this.element.current;
    if (!element || !Object.keys(this.props.errors).length) return;
    const field = element.querySelector<HTMLElement>(
      '[aria-invalid="true"], [data-invalid="true"]',
    );
    if (field) field.focus();
  }
  render(): ReactNode {
    return <div ref={this.element}>{this.props.children}</div>;
  }
}

class RecordEditorSession extends Component<SessionProps, EditorState> {
  state: EditorState = {
    preparation: { kind: "loading" },
    schema: { kind: "unselected" },
    dirty: false,
    discard: false,
    saving: false,
    mode: "fields",
  };
  private generation = 0;
  private schemaGeneration = 0;
  private readonly loader = new RecordLoader(this.props.onLoad);
  private readonly validator = customizeValidator<
    JsonObject,
    RJSFSchema,
    Record<string, never>
  >({ AjvClass: Ajv2020, ajvOptionsOverrides: { strict: false } });
  private readonly ContentForm = generateForm<
    JsonObject,
    RJSFSchema,
    Record<string, never>
  >();
  private readonly schemaForm =
    createRef<RjsfCoreForm<JsonObject, RJSFSchema, Record<string, never>>>();

  componentDidMount(): void {
    void this.prepare();
  }
  componentWillUnmount(): void {
    this.generation += 1;
    this.schemaGeneration += 1;
  }

  private async prepare(): Promise<void> {
    const generation = ++this.generation;
    this.setState({ preparation: { kind: "loading" } });
    try {
      const data = await this.loader.prepare(
        this.props.root,
        this.props.source,
      );
      if (generation !== this.generation) return;
      this.setState({ preparation: { kind: "ready", data }, dirty: false });
      if (data.draft.categoryId) await this.loadSchema(data);
    } catch (reason) {
      if (generation === this.generation)
        this.setState({
          preparation: { kind: "failed", message: contract.message(reason) },
        });
    }
  }

  private async loadSchema(data: PreparedRecord): Promise<void> {
    const generation = ++this.schemaGeneration;
    const choice = data.categories.find(
      (item) => item.value === data.draft.categoryId,
    );
    if (!choice) {
      this.setState({ schema: { kind: "unselected" } });
      return;
    }
    this.setState({ schema: { kind: "loading" } });
    try {
      const content = await this.loader.schema(choice, data.original);
      if (generation === this.schemaGeneration)
        this.setState({
          schema: { kind: "ready", content },
          mode: content.kind === "historical" ? "json" : this.state.mode,
        });
    } catch (reason) {
      if (generation === this.schemaGeneration)
        this.setState({
          schema: { kind: "failed", message: contract.message(reason) },
        });
    }
  }

  private change(update: Partial<RecordDraft>): void {
    const current = this.state.preparation;
    if (current.kind !== "ready") return;
    const data = {
      ...current.data,
      draft: { ...current.data.draft, ...update },
    };
    this.setState({
      preparation: { kind: "ready", data },
      dirty: true,
    });
    if (Object.hasOwn(update, "categoryId")) void this.loadSchema(data);
  }

  private resource(index: number, update: Partial<ResourceInput>): void {
    const current = this.state.preparation;
    if (current.kind === "ready")
      this.change({
        resources: current.data.draft.resources.map((resource, position) =>
          position === index ? { ...resource, ...update } : resource,
        ),
      });
  }

  private close(): void {
    if (this.state.saving) return;
    if (this.state.dirty) this.setState({ discard: true });
    else this.props.onClose();
  }

  private error(errors: Record<string, string>, field: string): string {
    const value = errors[field];
    return typeof value === "string" ? value : "";
  }

  private async submit(): Promise<void> {
    const current = this.state.preparation;
    if (current.kind !== "ready" || this.state.saving) return;
    const draft = current.data.draft;
    const errors: Record<string, string> = {};
    if (!draft.title.trim()) errors.title = "Enter a title.";
    if (!draft.categoryId) errors.category_id = "Choose a category.";
    if (!draft.tagIds.length) errors.tag_ids = "Choose at least one tag.";
    if (this.state.schema.kind !== "ready")
      errors.category_id = "Load the category schema before saving.";
    if (draft.resources.some((item) => !item.path.trim() || !item.language))
      errors.resources = "Every resource needs a path and language.";
    if (
      new Set(draft.resources.map((item) => item.path)).size !==
      draft.resources.length
    )
      errors.resources = "Resource paths must be unique.";
    let content: JsonObject = {};
    try {
      content = contract.parseContent(draft.content);
    } catch {
      errors.content = "Enter a valid JSON object.";
    }
    if (
      this.state.schema.kind === "ready" &&
      this.state.schema.content.kind === "available" &&
      !Object.hasOwn(errors, "content")
    ) {
      const validation = this.validator.validateFormData(
        content,
        this.state.schema.content.schema,
      );
      const form = this.schemaForm.current;
      if (form) form.validateForm();
      if (validation.errors.length)
        errors.content = validation.errors
          .map((error) => error.stack)
          .join("; ");
    }
    if (Object.keys(errors).length) {
      throw new RecordValidationError(errors);
    }
    const values = {
      title: draft.title,
      category_id: draft.categoryId,
      tag_ids: draft.tagIds,
      content,
      resources: draft.resources,
    };
    this.setState({ saving: true });
    try {
      const response = await this.props.execute(
        contract.writeAction(this.props.action, values),
        values,
      );
      if (response.kind !== "entity")
        throw new Error(
          "The server did not return the saved record. Reload before submitting again.",
        );
      contract.detail(response.entity);
      this.props.onSaved(response.entity);
    } catch (reason) {
      throw reason;
    } finally {
      this.setState({ saving: false });
    }
  }

  private content(data: PreparedRecord, error: string): ReactNode {
    const schema = this.state.schema;
    const draft = data.draft;
    if (schema.kind === "loading")
      return (
        <Skeleton
          height={80}
          aria-label="Loading category schema"
          role="status"
        />
      );
    if (schema.kind === "failed")
      return (
        <Alert color="red" title="Schema unavailable">
          <Stack>
            {schema.message}
            <Button onClick={() => void this.loadSchema(data)}>
              Retry schema
            </Button>
          </Stack>
        </Alert>
      );
    if (schema.kind === "unselected")
      return <Text c="dimmed">Choose a category to edit its content.</Text>;
    let parsed: Available<JsonObject>;
    try {
      parsed = {
        kind: "available",
        value: contract.parseContent(draft.content),
      };
    } catch {
      parsed = { kind: "unavailable" };
    }
    return (
      <Stack>
        <Text size="sm">
          Schema v{schema.content.version}
          {data.original.kind === "available" &&
          data.original.value.category.id === draft.categoryId
            ? " · Existing schema version preserved"
            : " · Selected category’s current schema"}
        </Text>
        {schema.content.kind === "historical" ? (
          <Alert title="JSON editing for this schema version">
            This record uses an older schema. Its exact schema is not available
            for generated fields. The server validates your changes against the
            assigned version.
          </Alert>
        ) : (
          <SegmentedControl
            aria-label="Content editor"
            value={this.state.mode}
            onChange={(mode) => this.setState({ mode })}
            data={[
              {
                label: "Fields",
                value: "fields",
                disabled: parsed.kind === "unavailable",
              },
              { label: "JSON", value: "json" },
            ]}
          />
        )}
        {schema.content.kind === "available" &&
        this.state.mode === "fields" &&
        parsed.kind === "available" ? (
          <>
            {error ? (
              <Alert color="red" role="alert" title="Content validation">
                {error}
              </Alert>
            ) : (
              <></>
            )}
            <this.ContentForm
              tagName="div"
              schema={schema.content.schema}
              validator={this.validator}
              formData={parsed.value}
              ref={this.schemaForm}
              templates={{ ArrayFieldTitleTemplate: RecordArrayTitle }}
              idPrefix="record-content"
              onChange={(
                event: IChangeEvent<
                  JsonObject,
                  RJSFSchema,
                  Record<string, never>
                >,
              ) => {
                if (event.formData !== undefined)
                  this.change({
                    content: JSON.stringify(event.formData, null, 2),
                  });
              }}
            >
              <></>
            </this.ContentForm>
          </>
        ) : (
          <JsonInput
            label="Content JSON"
            value={draft.content}
            onChange={(content) => this.change({ content })}
            autosize
            minRows={8}
            formatOnBlur
            error={error}
          />
        )}
      </Stack>
    );
  }

  private form(data: PreparedRecord): ReactNode {
    const draft = data.draft;
    return (
      <Form controls={[]} onSubmit={() => this.submit()}>
        {(errors) => (
          <RecordFields errors={errors}>
            <Stack gap="lg">
              <Fieldset legend="Basics" disabled={this.state.saving}>
                <Stack>
                  <TextInput
                    label="Title"
                    required
                    value={draft.title}
                    onChange={(event) =>
                      this.change({ title: event.currentTarget.value })
                    }
                    error={this.error(errors, "title")}
                    data-autofocus
                  />
                  <Select
                    label="Category"
                    required
                    searchable
                    data={data.categories}
                    value={draft.categoryId || null}
                    onChange={(value) =>
                      this.change({ categoryId: value === null ? "" : value })
                    }
                    error={this.error(errors, "category_id")}
                    nothingFoundMessage="No matching categories"
                  />
                  {!data.categories.length ? (
                    <Alert title="Create a category first">
                      No categories are available. Close this editor and open
                      Categories to create one.
                    </Alert>
                  ) : (
                    <></>
                  )}
                  <MultiSelect
                    label="Tags"
                    required
                    searchable
                    data={data.tags}
                    value={draft.tagIds}
                    onChange={(tagIds) => this.change({ tagIds })}
                    error={this.error(errors, "tag_ids")}
                    nothingFoundMessage="No matching tags"
                  />
                  {!data.tags.length ? (
                    <Alert title="Create a tag first">
                      At least one tag is required. Close this editor and open
                      Tags to create one.
                    </Alert>
                  ) : (
                    <></>
                  )}
                </Stack>
              </Fieldset>
              <Fieldset legend="Content" disabled={this.state.saving}>
                {this.content(data, this.error(errors, "content"))}
              </Fieldset>
              <Fieldset legend="Resources" disabled={this.state.saving}>
                <Stack>
                  <Text size="sm" c="dimmed">
                    Saving replaces the complete record and its attachments.
                  </Text>
                  {this.error(errors, "resources") ? (
                    <Alert color="red" role="alert" title="Resource validation">
                      {this.error(errors, "resources")}
                    </Alert>
                  ) : (
                    <></>
                  )}
                  {draft.resources.length ? (
                    <Accordion multiple>
                      {draft.resources.map((resource, index) => (
                        <Accordion.Item key={index} value={String(index)}>
                          <Accordion.Control>
                            {resource.path || `New resource ${index + 1}`}
                          </Accordion.Control>
                          <Accordion.Panel>
                            <Stack>
                              <TextInput
                                label="Resource path"
                                required
                                value={resource.path}
                                onChange={(event) =>
                                  this.resource(index, {
                                    path: event.currentTarget.value,
                                  })
                                }
                              />
                              <Select
                                label="Language"
                                required
                                searchable
                                data={data.languages}
                                value={resource.language || null}
                                onChange={(language) =>
                                  this.resource(index, {
                                    language: language === null ? "" : language,
                                  })
                                }
                              />
                              <Textarea
                                label="Source"
                                autosize
                                minRows={8}
                                value={resource.content}
                                onChange={(event) =>
                                  this.resource(index, {
                                    content: event.currentTarget.value,
                                  })
                                }
                              />
                              <Button
                                color="red"
                                variant="light"
                                onClick={() =>
                                  this.change({
                                    resources: draft.resources.filter(
                                      (_, position) => position !== index,
                                    ),
                                  })
                                }
                              >
                                Remove resource
                              </Button>
                            </Stack>
                          </Accordion.Panel>
                        </Accordion.Item>
                      ))}
                    </Accordion>
                  ) : (
                    <Text c="dimmed">No resources attached.</Text>
                  )}
                  <Button
                    variant="default"
                    onClick={() =>
                      this.change({
                        resources: [
                          ...draft.resources,
                          { path: "", language: "", content: "" },
                        ],
                      })
                    }
                  >
                    Add resource
                  </Button>
                </Stack>
              </Fieldset>
              <Group justify="flex-end">
                <Button
                  variant="default"
                  disabled={this.state.saving}
                  onClick={() => this.close()}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={this.state.saving}
                  disabled={
                    this.state.schema.kind !== "ready" ||
                    !data.categories.length ||
                    !data.tags.length
                  }
                >
                  {this.props.source.kind === "available"
                    ? "Save changes"
                    : "Create record"}
                </Button>
              </Group>
            </Stack>
          </RecordFields>
        )}
      </Form>
    );
  }

  render(): ReactNode {
    const prepared = this.state.preparation;
    return (
      <>
        <Drawer
          opened
          onClose={() => this.close()}
          position="right"
          size={this.props.narrow ? "100%" : "xl"}
          title={
            this.props.source.kind === "available"
              ? "Edit record"
              : "New record"
          }
          closeButtonProps={{
            "aria-label": "Close record editor",
            disabled: this.state.saving,
          }}
          closeOnEscape={!this.state.saving}
          closeOnClickOutside={!this.state.saving}
        >
          {prepared.kind === "loading" ? (
            <Stack role="status" aria-label="Preparing editor">
              <Text>Preparing editor…</Text>
              <Skeleton height={40} />
              <Skeleton height={160} />
            </Stack>
          ) : prepared.kind === "failed" ? (
            <Alert color="red" title="Editor unavailable">
              <Stack>
                {prepared.message}
                <Button onClick={() => void this.prepare()}>
                  Reload and retry
                </Button>
              </Stack>
            </Alert>
          ) : (
            this.form(prepared.data)
          )}
        </Drawer>
        <Modal
          opened={this.state.discard}
          onClose={() => this.setState({ discard: false })}
          title="Discard unsaved changes?"
          closeButtonProps={{ "aria-label": "Close discard confirmation" }}
        >
          <Stack>
            <Text>Your changes have not been saved.</Text>
            <Group justify="flex-end">
              <Button
                variant="default"
                onClick={() => this.setState({ discard: false })}
              >
                Keep editing
              </Button>
              <Button color="red" onClick={this.props.onClose}>
                Discard changes
              </Button>
            </Group>
          </Stack>
        </Modal>
      </>
    );
  }
}

export function RecordEditor(props: RecordEditorProps): ReactNode {
  const execution = useSirenActionExecution();
  const narrow = useMediaQuery("(max-width: 48em)") === true;
  return execution.kind === "available" ? (
    <RecordEditorSession
      {...props}
      execute={execution.execute}
      narrow={narrow}
    />
  ) : (
    <Alert color="red" title="Editor unavailable">
      <Stack>
        This surface cannot execute actions.
        <Button onClick={props.onClose}>Close</Button>
      </Stack>
    </Alert>
  );
}
