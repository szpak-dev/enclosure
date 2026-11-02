import {
  Alert,
  ActionIcon,
  Anchor,
  Group,
  List,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import type { SubEntity, Target } from "@siren-js/client";
import { IconArrowRight } from "@tabler/icons-react";
import { Component, type ReactNode } from "react";
import { scaffoldingPresentation } from "./ScaffoldingPresentation";

export type ScaffoldingListProps = {
  items: readonly SubEntity[];
  onFollow: (target: Target) => void;
};

export class ScaffoldingList extends Component<ScaffoldingListProps> {
  render(): ReactNode {
    const { items, onFollow } = this.props;
    if (!items.length)
      return (
        <Alert title="No scaffoldings found">
          No scaffolding matches this collection or search.
        </Alert>
      );
    return (
      <List
        listStyleType="none"
        spacing="lg"
        styles={{
          itemWrapper: { width: "100%" },
          itemLabel: { width: "100%" },
        }}
      >
        {items.map((item, index) => {
          const properties = scaffoldingPresentation.itemProperties(item);
          const id = scaffoldingPresentation.text(properties, "id");
          const name = scaffoldingPresentation.text(properties, "name");
          const target = scaffoldingPresentation.itemTarget(item);
          return (
            <List.Item key={`${id}-${index}`} px="md">
              <Group
                justify="space-between"
                wrap="nowrap"
                align="flex-start"
                w="100%"
              >
                <Stack gap="xs" miw={0} style={{ overflowWrap: "anywhere" }}>
                  <Stack gap={2}>
                    {target.kind === "present" ? (
                      <Anchor
                        fw={600}
                        href={`#${typeof target.target === "string" ? target.target : target.target.href}`}
                        onClick={(event) => {
                          event.preventDefault();
                          onFollow(target.target);
                        }}
                      >
                        {name}
                      </Anchor>
                    ) : (
                      <Text fw={600}>{name}</Text>
                    )}
                    <Text c="dimmed" size="sm">
                      {id}
                    </Text>
                  </Stack>
                  <Text size="sm">
                    Language:{" "}
                    {scaffoldingPresentation.text(properties, "language_id")}
                  </Text>
                  <Text c="dimmed" size="sm">
                    {scaffoldingPresentation.text(properties, "description")}
                  </Text>
                </Stack>
                {target.kind === "present" ? (
                  <Tooltip label={`Open ${name}`}>
                    <ActionIcon
                      component="a"
                      aria-label="Open scaffolding"
                      href={`#${typeof target.target === "string" ? target.target : target.target.href}`}
                      onClick={(event) => {
                        event.preventDefault();
                        onFollow(target.target);
                      }}
                      variant="subtle"
                    >
                      <IconArrowRight size={18} />
                    </ActionIcon>
                  </Tooltip>
                ) : (
                  <Text c="dimmed" size="sm">
                    This search result does not advertise a scaffolding
                    destination.
                  </Text>
                )}
              </Group>
            </List.Item>
          );
        })}
      </List>
    );
  }
}
