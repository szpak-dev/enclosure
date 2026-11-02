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
import { IconArrowRight } from "@tabler/icons-react";
import { Component, type ReactNode } from "react";
import { ResourcePage, Section } from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenContinuation } from "../siren/SirenContinuation";
import { ProjectActions } from "./ProjectActions";
import { projectPresentation } from "./ProjectPresentation";

export class ProjectCollection extends Component<SirenEntityProps> {
  render(): ReactNode {
    const { entity, onFollow, onRefresh } = this.props;
    return (
      <ResourcePage
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
            <List
              listStyleType="none"
              spacing="lg"
              styles={{
                itemWrapper: { width: "100%" },
                itemLabel: { width: "100%" },
              }}
            >
              {entity.entities.map((item, index) => {
                const properties = projectPresentation.itemProperties(item);
                const title = projectPresentation.text(properties, "title");
                const id = projectPresentation.text(properties, "id");
                const target = projectPresentation.itemTarget(item);
                return (
                  <List.Item key={`${id}-${index}`} px="md">
                    <Group
                      justify="space-between"
                      wrap="nowrap"
                      align="flex-start"
                      w="100%"
                    >
                      <Stack
                        gap={2}
                        miw={0}
                        style={{ overflowWrap: "anywhere" }}
                      >
                        {target.kind === "present" ? (
                          <Anchor
                            fw={600}
                            href={`#${typeof target.target === "string" ? target.target : target.target.href}`}
                            onClick={(event) => {
                              event.preventDefault();
                              onFollow(target.target);
                            }}
                          >
                            {title}
                          </Anchor>
                        ) : (
                          <Text fw={600}>{title}</Text>
                        )}
                        <Text c="dimmed" size="sm">
                          {id}
                        </Text>
                      </Stack>
                      {target.kind === "present" ? (
                        <Tooltip label={`Open ${title}`}>
                          <ActionIcon
                            component="a"
                            aria-label="Open project"
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
                          No destination advertised.
                        </Text>
                      )}
                    </Group>
                  </List.Item>
                );
              })}
            </List>
          ) : (
            <Alert title="No projects yet">
              Register a project to make its workspaces and governance resources
              available here.
            </Alert>
          )}
          <SirenContinuation entity={entity} onFollow={onFollow} />
        </Section>
      </ResourcePage>
    );
  }
}
