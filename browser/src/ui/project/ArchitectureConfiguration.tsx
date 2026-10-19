import {
  Alert,
  Button,
  Code,
  CopyButton,
  Group,
  Paper,
  ScrollArea,
  Stack,
  Table,
  Tabs,
  Text,
} from "@mantine/core";
import {
  Identity,
  PropertyTable,
  ResourcePage,
  Section,
} from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenContinuation } from "../siren/SirenContinuation";
import { projectPresentation } from "./ProjectPresentation";

export function ArchitectureConfigurationCollection({
  entity,
  onFollow,
}: SirenEntityProps) {
  return (
    <ResourcePage
      description="Revision-pinned Modwire boundary and architecture-shape configuration."
      title="Architecture configurations"
    >
      <Section title="Published configurations">
        {entity.entities.length ? (
          <Table.ScrollContainer
            minWidth={680}
            scrollAreaProps={{
              viewportProps: {
                "aria-label": "Published architecture configurations",
                tabIndex: 0,
              },
            }}
          >
            <Table withTableBorder>
              <Table.Caption>
                Published architecture configurations
              </Table.Caption>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Configuration ID</Table.Th>
                  <Table.Th>Revision</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {entity.entities.map((item, index) => {
                  const properties = projectPresentation.itemProperties(item);
                  const id = projectPresentation.text(properties, "id");
                  const target = projectPresentation.itemTarget(item);
                  return (
                    <Table.Tr key={`${id}-${index}`}>
                      <Table.Td>
                        <Code>{id}</Code>
                      </Table.Td>
                      <Table.Td>
                        <Code>
                          {projectPresentation.text(properties, "revision")}
                        </Code>
                      </Table.Td>
                      <Table.Td>
                        {target.kind === "present" ? (
                          <Button
                            component="a"
                            href={`#${typeof target.target === "string" ? target.target : target.target.href}`}
                            onClick={(event) => {
                              event.preventDefault();
                              onFollow(target.target);
                            }}
                            size="xs"
                            variant="light"
                          >
                            Open
                          </Button>
                        ) : (
                          <Text c="dimmed">Unavailable</Text>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        ) : (
          <Alert title="No architecture configuration">
            No configuration is advertised for this project.
          </Alert>
        )}
        <SirenContinuation entity={entity} onFollow={onFollow} />
      </Section>
    </ResourcePage>
  );
}

type DocumentPanelProps = { label: string; value: string };

function DocumentPanel({ label, value }: DocumentPanelProps) {
  return (
    <Stack>
      <Group justify="flex-end">
        <CopyButton value={value}>
          {({ copied, copy }) => (
            <Button onClick={copy} size="xs" variant="light">
              {copied ? "Copied" : `Copy ${label}`}
            </Button>
          )}
        </CopyButton>
      </Group>
      <ScrollArea.Autosize
        mah="36rem"
        type="auto"
        viewportProps={{
          "aria-label": `${label} document`,
          tabIndex: 0,
        }}
      >
        <Code aria-label={`${label} configuration`} block>
          {value}
        </Code>
      </ScrollArea.Autosize>
    </Stack>
  );
}

export function ArchitectureConfigurationEntity({ entity }: SirenEntityProps) {
  const id = projectPresentation.text(entity.properties, "id");
  const boundaries = projectPresentation.text(
    entity.properties,
    "boundaries_yaml",
  );
  const shape = projectPresentation.text(entity.properties, "shape_yaml");
  return (
    <ResourcePage
      description="Configuration metadata is separated from its complete YAML documents."
      title="Architecture configuration"
    >
      <Identity label="Configuration ID" value={id} />
      <Paper p="md" radius="md" withBorder>
        <PropertyTable
          caption="Architecture configuration metadata"
          label={(name) => projectPresentation.label(name)}
          properties={entity.properties}
          text={(properties, name) =>
            projectPresentation.text(properties, name)
          }
          visible={[
            "project_id",
            "revision",
            "boundaries_total_characters",
            "shape_total_characters",
          ]}
        />
      </Paper>
      <Tabs defaultValue="boundaries" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="boundaries">Boundaries</Tabs.Tab>
          <Tabs.Tab value="shape">Shape</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel pt="md" value="boundaries">
          <DocumentPanel label="boundaries YAML" value={boundaries} />
        </Tabs.Panel>
        <Tabs.Panel pt="md" value="shape">
          <DocumentPanel label="shape YAML" value={shape} />
        </Tabs.Panel>
      </Tabs>
    </ResourcePage>
  );
}
