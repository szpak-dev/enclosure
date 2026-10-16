import {
  ActionIcon,
  Box,
  Card,
  Code,
  Container,
  CopyButton,
  Group,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { IconCheck, IconCopy } from "@tabler/icons-react";
import type { Link, Target } from "@siren-js/client";
import type { ReactNode } from "react";
import { projectPresentation } from "./ProjectPresentation";

export type ProjectPageProps = {
  children: ReactNode;
  description: string;
  title: string;
};

export function ProjectPage({
  children,
  description,
  title,
}: ProjectPageProps) {
  return (
    <Container size="xl">
      <Stack gap="xl">
        <Stack gap={4}>
          <Title order={1}>{title}</Title>
          <Text c="dimmed">{description}</Text>
        </Stack>
        {children}
      </Stack>
    </Container>
  );
}

export type IdentityProps = {
  label: string;
  value: string;
};

export function Identity({ label, value }: IdentityProps) {
  return (
    <Group gap="xs" wrap="nowrap">
      <Text c="dimmed" size="sm">
        {label}
      </Text>
      <Code>{value}</Code>
      <CopyButton value={value}>
        {({ copied, copy }) => (
          <Tooltip label={copied ? "Copied" : `Copy ${label.toLowerCase()}`}>
            <ActionIcon
              aria-label={copied ? "Copied" : `Copy ${label.toLowerCase()}`}
              color={copied ? "teal" : "gray"}
              onClick={copy}
              size="sm"
              variant="subtle"
            >
              {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
            </ActionIcon>
          </Tooltip>
        )}
      </CopyButton>
    </Group>
  );
}

export type PropertyTableProps = {
  caption?: string;
  properties: object;
  visible: readonly string[];
};

export function PropertyTable({
  caption = "Details",
  properties,
  visible,
}: PropertyTableProps) {
  return (
    <Table.ScrollContainer
      minWidth={520}
      scrollAreaProps={{
        viewportProps: { "aria-label": caption, tabIndex: 0 },
      }}
    >
      <Table variant="vertical" withRowBorders>
        <Table.Caption>{caption}</Table.Caption>
        <Table.Tbody>
          {visible.map((name) => (
            <Table.Tr key={name}>
              <Table.Th>{projectPresentation.label(name)}</Table.Th>
              <Table.Td>
                <Text>{projectPresentation.text(properties, name)}</Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

export type ResourceCardsProps = {
  links: readonly Link[];
  onFollow: (target: Target) => void;
};

export function ResourceCards({ links, onFollow }: ResourceCardsProps) {
  if (!links.length)
    return <Text c="dimmed">No related resources advertised.</Text>;
  return (
    <SimpleGrid cols={{ base: 1, md: 2 }}>
      {links.map((link) => (
        <Card
          component="a"
          href={`#${link.href}`}
          key={link.href.toString()}
          onClick={(event) => {
            event.preventDefault();
            onFollow(link);
          }}
          padding="lg"
          radius="md"
          withBorder
        >
          <Stack gap={4}>
            <Text fw={600}>{projectPresentation.linkLabel(link)}</Text>
            <Text c="dimmed" size="sm">
              Open resource
            </Text>
          </Stack>
        </Card>
      ))}
    </SimpleGrid>
  );
}

export type SectionProps = {
  children: ReactNode;
  title: string;
};

export function Section({ children, title }: SectionProps) {
  return (
    <Box component="section">
      <Stack>
        <Title order={2} size="h3">
          {title}
        </Title>
        {children}
      </Stack>
    </Box>
  );
}
