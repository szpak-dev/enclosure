import type { Field } from "@siren-js/client";
import { getDefaultFormState, type RJSFSchema } from "@rjsf/utils";
import { JsonEditor, type JsonData } from "json-edit-react";
import { useState } from "react";
import type { FormSchemaProperty } from "../../form/FormSchema";
import { useFormValue } from "../../form/FormValueRegistry";
import { jsonSchemaValidator } from "../../form/JsonSchemaValidator";

export type SirenJsonInputProps = {
  field: Field;
  schema: FormSchemaProperty;
};

export function SirenJsonInput({ field, schema }: SirenJsonInputProps) {
  const [value, setValue] = useState<JsonData>(() =>
    getDefaultFormState(jsonSchemaValidator, schema as RJSFSchema, field.value),
  );
  const publishValue = useFormValue(field.name, value);

  const updateValue = (nextValue: JsonData) => {
    setValue(nextValue);
    publishValue(nextValue);
  };

  return (
    <JsonEditor
      data={value}
      rootName={field.name}
      setData={updateValue}
      showCollectionCount="when-closed"
      showIconTooltips
      theme={{
        container: {
          backgroundColor: "var(--mantine-color-body)",
          color: "var(--mantine-color-text)",
        },
        property: "var(--mantine-color-text)",
        string: "var(--mantine-color-text)",
        number: "var(--mantine-color-text)",
        boolean: "var(--mantine-color-text)",
        null: "var(--mantine-color-dimmed)",
        bracket: "var(--mantine-color-dimmed)",
        itemCount: "var(--mantine-color-dimmed)",
      }}
    />
  );
}
