import { Button, Fieldset, Stack } from "@mantine/core";
import { Field, type Action } from "@siren-js/client";
import { useState } from "react";
import { Form } from "../form/Form";
import { FormField } from "../form/FormField";
import type { FormSchema, FormSchemaProperty } from "../form/FormSchema";
import type { FormControl } from "../form/FormValues";
import { SirenField } from "./SirenField";
import { SirenJsonInput } from "./inputs/SirenJsonInput";
import { SirenStructuredInput } from "./inputs/SirenStructuredInput";

export const STRUCTURED_FORM_EXTENSION =
  "https://modwire.dev/siren/structured-form/v1";
export const JSON_CONTROL = "https://modwire.dev/siren/controls/json/v1";
export const OBJECT_CONTROL = "https://modwire.dev/siren/controls/object/v1";
export const ARRAY_CONTROL = "https://modwire.dev/siren/controls/array/v1";

export type SirenActionFormProps = {
  action: Action;
  values?: object;
  onSubmit: (
    action: Action,
    values: Record<string, unknown>,
  ) => Promise<void> | void;
};

function structuredFieldType(
  schema: FormSchemaProperty,
): "list" | "object" | undefined {
  const types = Array.isArray(schema.type)
    ? schema.type
    : schema.type
      ? [schema.type]
      : [];
  if (types.includes("object") || schema.properties) return "object";
  if (types.includes("array") || schema.items) return "list";
  return undefined;
}

function formControl(field: Field): FormControl {
  if (field.type === "checkbox")
    return { name: field.name, valueType: "boolean" };
  if (field.type === "number" || field.type === "range")
    return { name: field.name, valueType: "number" };
  return { name: field.name };
}

function actionFields(
  action: Action,
  schema?: FormSchema,
  values: object = {},
): Field[] {
  const initialValues = record(values) ?? {};
  const fields = action.fields.map((field) =>
    field.value === undefined && Object.hasOwn(initialValues, field.name)
      ? Object.assign(new Field(), field, {
          value: initialValues[field.name],
        })
      : field,
  );
  const present = new Set(fields.map((field) => field.name));

  for (const [name, property] of Object.entries(schema?.properties ?? {})) {
    const type = structuredFieldType(property);
    if (!type || present.has(name)) continue;
    fields.push(
      Object.assign(new Field(), {
        name,
        title: property.title ?? name,
        type,
        value: Object.hasOwn(initialValues, name)
          ? initialValues[name]
          : undefined,
      }),
    );
  }

  return fields;
}

function record(value: unknown): Record<string, unknown> | undefined {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

type StructuredControl = {
  control: string;
  name: string;
  required: boolean;
  schema: FormSchemaProperty;
};

function actionFieldInput(field: Field, control?: StructuredControl) {
  if (!control) return <SirenField field={field} />;

  switch (control.control) {
    case JSON_CONTROL:
      return <SirenJsonInput field={field} schema={control.schema} />;
    case OBJECT_CONTROL:
    case ARRAY_CONTROL:
      return <SirenStructuredInput field={field} schema={control.schema} />;
    default:
      throw new Error(`Unsupported Siren control: ${control.control}`);
  }
}

function structuredControls(action: Action): StructuredControl[] {
  const value = action[STRUCTURED_FORM_EXTENSION];
  if (value === undefined) return [];

  const extension = record(value);
  if (
    !extension ||
    extension.version !== "1" ||
    !Array.isArray(extension.controls)
  )
    throw new Error("Malformed Siren structured-form extension");

  return extension.controls.map((value) => {
    const control = record(value);
    if (!control) throw new Error("Malformed Siren structured-form control");
    const schema = record(control.schema);
    if (
      typeof control.control !== "string" ||
      typeof control.name !== "string" ||
      control.location !== "body" ||
      typeof control.required !== "boolean" ||
      control.mediaType !== "application/json" ||
      !schema
    )
      throw new Error("Malformed Siren structured-form control");

    return {
      control: control.control,
      name: control.name,
      required: control.required,
      schema: schema as FormSchemaProperty,
    };
  });
}

function structuredFormSchema(
  controls: StructuredControl[],
): FormSchema | undefined {
  if (controls.length) {
    return {
      properties: Object.fromEntries(
        controls.map((control) => [control.name, control.schema]),
      ),
      required: controls
        .filter((control) => control.required === true)
        .map((control) => control.name),
      type: "object",
    };
  }
  return undefined;
}

export function SirenActionForm({
  action,
  onSubmit,
  values,
}: SirenActionFormProps) {
  const [submitting, setSubmitting] = useState(false);
  const controls = structuredControls(action);
  const schema = structuredFormSchema(controls);
  const fields = actionFields(action, schema, values);
  const controlsByName = new Map(
    controls.map((control) => [control.name, control]),
  );

  return (
    <Form
      controls={fields.map(formControl)}
      onSubmit={async (values) => {
        action.fields = fields;
        setSubmitting(true);
        try {
          await onSubmit(action, values);
        } finally {
          setSubmitting(false);
        }
      }}
      {...(schema ? { schema } : {})}
    >
      {(errors) => (
        <Fieldset legend={action.title}>
          <Stack gap="sm">
            {fields.map((field) => {
              const control = controlsByName.get(field.name);
              return (
                <FormField
                  key={field.name}
                  label={field.title ?? field.name}
                  {...(errors[field.name] ? { error: errors[field.name] } : {})}
                >
                  {actionFieldInput(field, control)}
                </FormField>
              );
            })}
            <Button loading={submitting} type="submit">
              {action.title}
            </Button>
          </Stack>
        </Fieldset>
      )}
    </Form>
  );
}
