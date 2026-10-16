import { Alert, Button, Code, Table, Text } from "@mantine/core";
import { ResourcePage, Section } from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenContinuation } from "../siren/SirenContinuation";
import { ProjectActions } from "./ProjectActions";
import { projectPresentation } from "./ProjectPresentation";

export function WorkspaceCollection({
  entity,
  onFollow,
  onRefresh,
}: SirenEntityProps) {
  return (
    <ResourcePage
      description="Explicit local checkouts bound to this logical project."
      title="Workspaces"
    >
      <ProjectActions
        actions={entity.actions}
        dangerNames={[]}
        omitNames={["find_workspaces"]}
        onRefresh={onRefresh}
        primaryName="bind_workspace"
        values={entity.properties}
      />
      <Section title="Bound workspaces">
        {entity.entities.length ? (
          <Table.ScrollContainer
            minWidth={760}
            scrollAreaProps={{
              viewportProps: {
                "aria-label": "Bound workspaces",
                tabIndex: 0,
              },
            }}
          >
            <Table highlightOnHover verticalSpacing="sm" withTableBorder>
              <Table.Caption>Bound workspaces</Table.Caption>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Workspace root</Table.Th>
                  <Table.Th>Architecture root</Table.Th>
                  <Table.Th>Revision</Table.Th>
                  <Table.Th>Workspace ID</Table.Th>
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
                        <Text fw={600}>
                          {projectPresentation.text(properties, "root")}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        {projectPresentation.text(
                          properties,
                          "architecture_root",
                        )}
                      </Table.Td>
                      <Table.Td>
                        {projectPresentation.text(properties, "revision")}
                      </Table.Td>
                      <Table.Td>
                        <Code>{id}</Code>
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
                          <Text c="dimmed" size="sm">
                            Unavailable
                          </Text>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        ) : (
          <Alert title="No workspaces bound">
            Bind a local checkout before generating source or checking health.
          </Alert>
        )}
        <SirenContinuation entity={entity} onFollow={onFollow} />
      </Section>
    </ResourcePage>
  );
}
