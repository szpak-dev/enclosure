import {
  Alert,
  Button,
  Card,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenContinuation } from "../siren/SirenContinuation";
import { ProjectActions } from "./ProjectActions";
import { Identity, ProjectPage, Section } from "./ProjectPrimitives";
import { projectPresentation } from "./ProjectPresentation";

export function ProjectCollection({
  entity,
  onFollow,
  onRefresh,
}: SirenEntityProps) {
  return (
    <ProjectPage
      description="Registered software systems and their governed delivery resources."
      title="Projects"
    >
      <ProjectActions
        actions={entity.actions}
        dangerNames={[]}
        omitNames={["find_projects"]}
        onRefresh={onRefresh}
        primaryName="register_project"
        values={entity.properties}
      />
      <Section title="Registered projects">
        {entity.entities.length ? (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
            {entity.entities.map((item, index) => {
              const properties = projectPresentation.itemProperties(item);
              const title = projectPresentation.text(properties, "title");
              const id = projectPresentation.text(properties, "id");
              const target = projectPresentation.itemTarget(item);
              return (
                <Card
                  key={`${id}-${index}`}
                  padding="lg"
                  radius="md"
                  withBorder
                >
                  <Stack justify="space-between" mih={150}>
                    <Stack gap="xs">
                      <Title order={3}>{title}</Title>
                      <Identity label="Project ID" value={id} />
                    </Stack>
                    {target.kind === "present" ? (
                      <Button
                        component="a"
                        href={`#${typeof target.target === "string" ? target.target : target.target.href}`}
                        onClick={(event) => {
                          event.preventDefault();
                          onFollow(target.target);
                        }}
                        variant="light"
                      >
                        Open project
                      </Button>
                    ) : (
                      <Text c="dimmed" size="sm">
                        No destination advertised.
                      </Text>
                    )}
                  </Stack>
                </Card>
              );
            })}
          </SimpleGrid>
        ) : (
          <Alert title="No projects yet">
            Register a project to make its workspaces and governance resources
            available here.
          </Alert>
        )}
        <SirenContinuation entity={entity} onFollow={onFollow} />
      </Section>
    </ProjectPage>
  );
}
