import { Alert } from "@mantine/core";

export type FormErrorsProps = { errors: Record<string, string> };

export function FormErrors({ errors }: FormErrorsProps) {
  const messages = Object.values(errors);
  if (!messages.length) return null;
  return (
    <Alert color="red" role="alert" title="Please fix the highlighted fields">
      {messages.join(" ")}
    </Alert>
  );
}
