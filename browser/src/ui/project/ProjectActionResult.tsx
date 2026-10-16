import {
  Accordion,
  Alert,
  Badge,
  Button,
  Code,
  Group,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import type { Entity } from "@siren-js/client";
import { projectPresentation } from "./ProjectPresentation";

export type ProjectActionResultProps = {
  actionName: string;
  entity: Entity;
};

function isStructured(value: unknown): value is object {
  return typeof value === "object" && value !== null;
}

function StructuredValue({ value }: { value: object }) {
  if (Array.isArray(value)) {
    if (!value.length) return <Text c="dimmed">No items reported.</Text>;
    return (
      <Stack gap="xs">
        {value.map((item, index) => (
          <Paper key={index} p="sm" radius="sm" withBorder>
            {isStructured(item) ? (
              <StructuredValue value={item} />
            ) : (
              <Text>{item === null ? "Not reported" : String(item)}</Text>
            )}
          </Paper>
        ))}
      </Stack>
    );
  }

  const entries = Object.entries(value);
  if (!entries.length) return <Text c="dimmed">No details reported.</Text>;
  return (
    <Stack gap="xs">
      {entries.map(([name, nested]) => (
        <Paper key={name} p="sm" radius="sm" withBorder>
          <Stack gap={4}>
            <Text c="dimmed" fw={600} size="sm">
              {projectPresentation.label(name)}
            </Text>
            {isStructured(nested) ? (
              <StructuredValue value={nested} />
            ) : typeof nested === "string" && nested.length > 80 ? (
              <Code>{nested}</Code>
            ) : (
              <Text>
                {nested === null || nested === undefined
                  ? "Not reported"
                  : String(nested)}
              </Text>
            )}
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}

export function ProjectActionResult({
  actionName,
  entity,
}: ProjectActionResultProps) {
  const entries = Object.entries(entity.properties);
  const summary = entries.filter(([, value]) => !isStructured(value));
  const details = entries.filter((entry): entry is [string, object] =>
    isStructured(entry[1]),
  );
  const status = ["status", "state", "conclusion", "healthy"]
    .map((name) => projectPresentation.value(entity.properties, name))
    .find((value) => value.kind === "present");

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={3}>{entity.title || "Action result"}</Title>
        {status && status.kind === "present" ? (
          <Badge variant="light">{String(status.value)}</Badge>
        ) : null}
      </Group>
      {actionName === "check_project_health" ? (
        <Alert
          color={
            projectPresentation.text(entity.properties, "healthy") === "Yes"
              ? "teal.9"
              : "yellow.9"
          }
          title="Project health"
          variant="outline"
        >
          This result is revision-scoped. Open the advertised findings and
          attestation resources for complete evidence.
        </Alert>
      ) : null}
      {summary.length ? (
        <Table variant="vertical" withRowBorders>
          <Table.Caption>Action result summary</Table.Caption>
          <Table.Tbody>
            {summary.map(([name, value]) => (
              <Table.Tr key={name}>
                <Table.Th>{projectPresentation.label(name)}</Table.Th>
                <Table.Td>
                  {typeof value === "string" && value.length > 80 ? (
                    <Code>{value}</Code>
                  ) : (
                    <Text>{String(value)}</Text>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : null}
      {details.length ? (
        <Accordion variant="separated">
          {details.map(([name, value]) => (
            <Accordion.Item key={name} value={name}>
              <Accordion.Control>
                {projectPresentation.label(name)}
              </Accordion.Control>
              <Accordion.Panel>
                <StructuredValue value={value} />
              </Accordion.Panel>
            </Accordion.Item>
          ))}
        </Accordion>
      ) : null}
      {entity.links.length ? (
        <Stack gap="xs">
          <Text fw={600}>Available evidence</Text>
          <Group>
            {entity.links
              .filter((link) => !link.rel.includes("self"))
              .map((link) => (
                <Button
                  component="a"
                  href={`#${link.href}`}
                  key={link.href.toString()}
                  variant="light"
                >
                  {projectPresentation.linkLabel(link)}
                </Button>
              ))}
          </Group>
        </Stack>
      ) : null}
    </Stack>
  );
}
