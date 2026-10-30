import {
  Accordion,
  ActionIcon,
  Alert,
  Anchor,
  Badge,
  Button,
  Code,
  Group,
  List,
  SegmentedControl,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import { IconArrowRight, IconPencil } from "@tabler/icons-react";
import type { Action, Entity, SubEntity, Target } from "@siren-js/client";
import { Component, type ReactNode } from "react";
import {
  recordContract as contract,
  type JsonValue,
  type RecordSummary,
} from "./RecordContract";

export class RecordBoundary extends Component<
  { children: ReactNode; entity: Entity; onRefresh: () => void },
  { failure: string }
> {
  state = { failure: "" };
  componentDidCatch(error: Error): void {
    this.setState({ failure: error.message });
  }
  componentDidUpdate(
    previous: Readonly<{
      children: ReactNode;
      entity: Entity;
      onRefresh: () => void;
    }>,
  ): void {
    if (previous.entity !== this.props.entity && this.state.failure)
      this.setState({ failure: "" });
  }
  render(): ReactNode {
    return this.state.failure ? (
      <Alert color="red" role="alert" title="Records view unavailable">
        <Stack>
          {this.state.failure}
          <Button onClick={this.props.onRefresh}>Reload</Button>
        </Stack>
      </Alert>
    ) : (
      this.props.children
    );
  }
}

export function RecordLink({
  target,
  children,
  onFollow,
}: {
  target: Target;
  children: ReactNode;
  onFollow: (target: Target) => void;
}): ReactNode {
  return (
    <Anchor
      href={`#${contract.href(target)}`}
      onClick={(event) => {
        event.preventDefault();
        onFollow(target);
      }}
    >
      {children}
    </Anchor>
  );
}

export function RecordBadges({ record }: { record: RecordSummary }): ReactNode {
  return (
    <Stack gap={4}>
      <Text size="sm" c="dimmed">
        {record.category.title} · Schema v{record.version}
      </Text>
      <Group gap={4}>
        {record.tags.map((tag) => (
          <Badge key={tag.id} variant="light">
            {tag.name}
          </Badge>
        ))}
      </Group>
    </Stack>
  );
}

export function RecordRows({
  items,
  onFollow,
  onEdit,
}: {
  items: readonly SubEntity[];
  onFollow: (target: Target) => void;
  onEdit: (action: Action, target: Target) => void;
}): ReactNode {
  return (
    <List
      listStyleType="none"
      spacing="md"
      styles={{ itemWrapper: { width: "100%" }, itemLabel: { width: "100%" } }}
    >
      {items.map((item) => {
        const record = contract.summary(contract.properties(item));
        const target = contract.target(item);
        const edit = contract.action(item, "update_record");
        return (
          <List.Item key={record.id}>
            <Group
              justify="space-between"
              wrap="nowrap"
              align="flex-start"
              w="100%"
            >
              <Stack gap={4} flex={1} miw={0}>
                {target.kind === "available" ? (
                  <RecordLink target={target.value} onFollow={onFollow}>
                    {record.title}
                  </RecordLink>
                ) : (
                  <Text>{record.title}</Text>
                )}
                <RecordBadges record={record} />
              </Stack>
              <Group gap={4} wrap="nowrap">
                {edit.kind === "available" && target.kind === "available" ? (
                  <Tooltip label="Edit record">
                    <ActionIcon
                      variant="subtle"
                      aria-label={`Edit ${record.title}`}
                      onClick={() => onEdit(edit.value, target.value)}
                    >
                      <IconPencil size={18} />
                    </ActionIcon>
                  </Tooltip>
                ) : (
                  <></>
                )}
                {target.kind === "available" ? (
                  <Tooltip label="Open record">
                    <ActionIcon
                      component="a"
                      href={`#${contract.href(target.value)}`}
                      variant="subtle"
                      aria-label={`Open ${record.title}`}
                      onClick={(event) => {
                        event.preventDefault();
                        onFollow(target.value);
                      }}
                    >
                      <IconArrowRight size={18} />
                    </ActionIcon>
                  </Tooltip>
                ) : (
                  <Text size="sm">Navigation unavailable</Text>
                )}
              </Group>
            </Group>
          </List.Item>
        );
      })}
    </List>
  );
}

export function RecordValue({ value }: { value: JsonValue }): ReactNode {
  if (value === null) return <Code>null</Code>;
  if (typeof value === "string")
    return (
      <Text style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
        {value.length ? value : "(empty text)"}
      </Text>
    );
  if (typeof value === "number" || typeof value === "boolean")
    return <Text>{String(value)}</Text>;
  if (Array.isArray(value))
    return value.length ? (
      <List spacing="xs">
        {value.map((item, index) => (
          <List.Item key={index}>
            <RecordValue value={item} />
          </List.Item>
        ))}
      </List>
    ) : (
      <Text c="dimmed">Empty list</Text>
    );
  const entries = Object.entries(value);
  return entries.length ? (
    <Stack gap="md">
      {entries.map(([name, item]) =>
        typeof item === "object" && item !== null ? (
          <Accordion key={name} variant="contained">
            <Accordion.Item value={name}>
              <Accordion.Control>{name}</Accordion.Control>
              <Accordion.Panel>
                <RecordValue value={item} />
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        ) : (
          <Stack gap={4} key={name}>
            <Text fw={600}>{name}</Text>
            <RecordValue value={item} />
          </Stack>
        ),
      )}
    </Stack>
  ) : (
    <Text c="dimmed">Empty object</Text>
  );
}

export class RecordContent extends Component<
  { value: JsonValue },
  { mode: string }
> {
  state = { mode: "reading" };
  render(): ReactNode {
    return (
      <Stack>
        <SegmentedControl
          aria-label="Content presentation"
          value={this.state.mode}
          onChange={(mode) => this.setState({ mode })}
          data={[
            { label: "Reading", value: "reading" },
            { label: "JSON", value: "json" },
          ]}
        />
        {this.state.mode === "reading" ? (
          <RecordValue value={this.props.value} />
        ) : (
          <Code block>{JSON.stringify(this.props.value, null, 2)}</Code>
        )}
      </Stack>
    );
  }
}
