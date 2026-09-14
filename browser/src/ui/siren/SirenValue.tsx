import { Text } from "@mantine/core";
import JsonView from "@uiw/react-json-view";

export type SirenPropertyValue = string | number | boolean | object;

export type SirenValueProps = { value: SirenPropertyValue };

export function SirenValue({ value }: SirenValueProps) {
  if (typeof value === "boolean") return <Text>{value ? "Yes" : "No"}</Text>;
  if (typeof value === "string" || typeof value === "number")
    return <Text>{String(value)}</Text>;
  return (
    <JsonView
      collapsed={false}
      displayDataTypes={false}
      enableClipboard={false}
      value={value}
    />
  );
}
