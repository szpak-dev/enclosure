import { Alert, Button, Loader, Select, Stack } from "@mantine/core";
import { Action, Field, type Entity, type Target } from "@siren-js/client";
import { useEffect, useState } from "react";
import { SirenResponseError } from "../../client/SirenClient";
import type { FormSchemaProperty } from "../form/FormSchema";
import {
  OBJECT_CONTROL,
  SirenActionForm,
  STRUCTURED_FORM_EXTENSION,
} from "../siren/SirenActionForm";

type StructuredControl = {
  control: string;
  location: string;
  mediaType: string;
  name: string;
  required: boolean;
  schema: FormSchemaProperty;
};

type StructuredForm = {
  controls: StructuredControl[];
  version: string;
};

type CommandContract = {
  arguments: StructuredControl;
  operation: Field;
  revision: Field;
  structuredForm: StructuredForm;
};

type DiagramCommandFormProps = {
  action: Action;
  kind: string;
  onLoad: (target: Target) => Promise<Entity>;
  onRefresh: () => void;
  onSubmit: (
    action: Action,
    values: Record<string, unknown>,
  ) => Promise<void> | void;
  revision: number;
  root: Entity;
};

type CommandSchemas = Record<string, FormSchemaProperty>;

function commandContract(action: Action): CommandContract | undefined {
  const structuredForm = action[STRUCTURED_FORM_EXTENSION] as
    StructuredForm | undefined;
  const revision = action.fields.find((field) => field.type === "number");
  const operation = action.fields.find((field) => field.type === "text");
  const argumentsControl = structuredForm?.controls[0];

  if (!structuredForm || !revision || !operation || !argumentsControl)
    return undefined;

  return {
    arguments: argumentsControl,
    operation,
    revision,
    structuredForm,
  };
}

export function isDiagramCommandAction(action: Action): boolean {
  return commandContract(action) !== undefined;
}

function selfTarget(entity: Entity): Target | undefined {
  return entity.links.find((link) => link.rel.includes("self"));
}

async function loadKind(
  root: Entity,
  kind: string,
  onLoad: (target: Target) => Promise<Entity>,
): Promise<Entity> {
  const collections = root.links.filter((link) =>
    link.rel.includes("collection"),
  );

  for (const target of collections) {
    const collection = await onLoad(target);
    const item = collection.entities.find(
      (entity) =>
        (entity.properties as Record<string, unknown> | undefined)?.id === kind,
    );
    const itemTarget = item && selfTarget(item as unknown as Entity);
    if (itemTarget) return onLoad(itemTarget);
  }

  throw new Error(`Diagram kind ${kind} is not advertised.`);
}

function operationLabel(operation: string): string {
  const label = operation.replaceAll("_", " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function commandAction(
  action: Action,
  contract: CommandContract,
  operation: string,
  revision: number,
  schema: FormSchemaProperty,
): Action {
  const fields = action.fields.map((field) =>
    Object.assign(new Field(), field, {
      type:
        field.name === contract.operation.name ||
        field.name === contract.revision.name
          ? "hidden"
          : field.type,
      value:
        field.name === contract.operation.name
          ? operation
          : field.name === contract.revision.name
            ? revision
            : field.value,
    }),
  );
  const structuredForm = {
    ...contract.structuredForm,
    controls: contract.structuredForm.controls.map((control) =>
      control.name === contract.arguments.name
        ? { ...control, control: OBJECT_CONTROL, schema }
        : control,
    ),
  };

  return Object.assign(new Action(), action, {
    fields,
    [STRUCTURED_FORM_EXTENSION]: structuredForm,
  });
}

export function DiagramCommandForm({
  action,
  kind,
  onLoad,
  onRefresh,
  onSubmit,
  revision,
  root,
}: DiagramCommandFormProps) {
  const [description, setDescription] = useState<Entity | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [operation, setOperation] = useState<string | null>(null);
  const [revisionConflict, setRevisionConflict] = useState(false);
  const contract = commandContract(action);

  useEffect(() => {
    let current = true;
    setDescription(null);
    setError(null);
    void loadKind(root, kind, onLoad).then(
      (entity) => current && setDescription(entity),
      (reason) =>
        current &&
        setError(
          reason instanceof Error
            ? reason
            : new Error("Unable to load diagram commands."),
        ),
    );
    return () => {
      current = false;
    };
  }, [kind, onLoad, root]);

  if (!contract) return null;
  if (error)
    return (
      <Alert color="red" role="alert" title="Diagram commands unavailable">
        {error.message}
      </Alert>
    );
  if (!description)
    return <Loader aria-label="Loading diagram commands" size="sm" />;

  const commands = (description.properties as Record<string, unknown>)
    .commands as CommandSchemas;
  const operations = Object.keys(commands);
  const selectedOperation =
    operation && operations.includes(operation) ? operation : operations[0];
  const selectedAction = commandAction(
    action,
    contract,
    selectedOperation,
    revision,
    commands[selectedOperation],
  );

  const submit = async (
    submittedAction: Action,
    values: Record<string, unknown>,
  ) => {
    try {
      await onSubmit(submittedAction, {
        ...values,
        [contract.operation.name]: selectedOperation,
        [contract.revision.name]: revision,
      });
      setRevisionConflict(false);
    } catch (reason) {
      setRevisionConflict(
        reason instanceof SirenResponseError &&
          reason.message.includes("revision conflict"),
      );
      throw reason;
    }
  };

  return (
    <Stack>
      <Select
        data={operations.map((value) => ({
          label: operationLabel(value),
          value,
        }))}
        label={contract.operation.title ?? contract.operation.name}
        onChange={setOperation}
        value={selectedOperation}
      />
      {revisionConflict ? (
        <Alert color="yellow" role="alert" title="Diagram changed">
          <Stack gap="xs">
            Refresh the diagram and retry the command with the current revision.
            <Button
              onClick={() => {
                setRevisionConflict(false);
                onRefresh();
              }}
              size="xs"
              variant="light"
            >
              Refresh diagram
            </Button>
          </Stack>
        </Alert>
      ) : null}
      <SirenActionForm
        action={selectedAction}
        key={selectedOperation}
        onSubmit={submit}
      />
    </Stack>
  );
}
