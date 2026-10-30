import {
  Accordion,
  Alert,
  Badge,
  Button,
  Group,
  List,
  Stack,
  Text,
} from "@mantine/core";
import type { Entity } from "@siren-js/client";
import { Component, type ReactNode } from "react";
import {
  Identity,
  ResourcePage,
  Section,
} from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { recordContract as contract, type Available } from "./RecordContract";
import {
  RecordBadges,
  RecordBoundary,
  RecordContent,
} from "./RecordPrimitives";
import { RecordActions } from "./RecordActions";
import { RecordEditor } from "./RecordEditor";

type DetailState = { editing: boolean; saved: Available<Entity> };

export class RecordDetailView extends Component<SirenEntityProps, DetailState> {
  state: DetailState = { editing: false, saved: { kind: "unavailable" } };
  componentDidUpdate(previous: SirenEntityProps): void {
    if (previous.entity !== this.props.entity)
      this.setState({ editing: false, saved: { kind: "unavailable" } });
  }

  render(): ReactNode {
    const entity =
      this.state.saved.kind === "available"
        ? this.state.saved.value
        : this.props.entity;
    const record = contract.detail(entity);
    const edit = contract.action(entity, "update_record");
    const target = contract.target(entity);
    const resourceAction = contract.action(entity, "read_record_resource");
    const contentAction = contract.action(entity, "read_record_content");
    const manifestLink = entity.links.find(
      (link) =>
        link.rel.includes("collection") &&
        new URL(contract.href(link), window.location.origin).pathname.endsWith(
          "/resource-manifests",
        ),
    );
    return (
      <ResourcePage
        title={record.title}
        description="Record content and attached source resources."
      >
        <Group justify="flex-end">
          {edit.kind === "available" && target.kind === "available" ? (
            <Button onClick={() => this.setState({ editing: true })}>
              Edit record
            </Button>
          ) : (
            <></>
          )}
        </Group>
        {this.state.saved.kind === "available" ? (
          <Alert
            color="teal.9"
            variant="filled"
            autoContrast
            role="status"
            title="Record saved"
          >
            Your changes have been saved.
          </Alert>
        ) : (
          <></>
        )}
        <RecordBadges record={record} />
        <Section title="Content">
          <RecordContent value={record.content} />
          {contentAction.kind === "available" ? (
            <Button
              variant="subtle"
              onClick={() =>
                this.props.onFollow(
                  contract.query(contentAction.value, {
                    expected_revision: record.contentRevision,
                    offset: 0,
                    limit: 10000,
                  }),
                )
              }
            >
              Read source pages
            </Button>
          ) : (
            <></>
          )}
        </Section>
        <Section title={`Resources (${record.resourceCount})`}>
          {record.resources.length ? (
            <List
              listStyleType="none"
              spacing="sm"
              styles={{
                itemWrapper: { width: "100%" },
                itemLabel: { width: "100%" },
              }}
            >
              {record.resources.map((resource) => (
                <List.Item key={resource.path}>
                  <Group justify="space-between" wrap="nowrap" w="100%">
                    <Stack gap={4} miw={0}>
                      <Text fw={600} style={{ overflowWrap: "anywhere" }}>
                        {resource.path}
                      </Text>
                      <Group gap="xs">
                        <Badge variant="light">{resource.language}</Badge>
                        <Text c="dimmed" size="sm">
                          {resource.size} bytes · {resource.mediaType}
                        </Text>
                      </Group>
                    </Stack>
                    {resourceAction.kind === "available" ? (
                      <Button
                        variant="light"
                        onClick={() =>
                          this.props.onFollow(
                            contract.query(resourceAction.value, {
                              path: resource.path,
                              expected_revision: resource.revision,
                              offset: 0,
                              limit: 10000,
                            }),
                          )
                        }
                        aria-label={`Open ${resource.path}`}
                      >
                        Open
                      </Button>
                    ) : (
                      <Text size="sm">Content unavailable</Text>
                    )}
                  </Group>
                </List.Item>
              ))}
            </List>
          ) : (
            <Text c="dimmed">No resources attached.</Text>
          )}
          {manifestLink ? (
            <Button
              variant="default"
              onClick={() =>
                this.props.onFollow(
                  contract.query(manifestLink, {
                    expected_revision: record.resourcesRevision,
                    offset: 0,
                    limit: 50,
                  }),
                )
              }
            >
              Browse resource manifests
            </Button>
          ) : (
            <></>
          )}
        </Section>
        <Accordion>
          <Accordion.Item value="technical">
            <Accordion.Control>Technical details</Accordion.Control>
            <Accordion.Panel>
              <Stack>
                <Identity label="Record ID" value={record.id} />
                <Identity
                  label="Content revision"
                  value={record.contentRevision}
                />
                <Identity
                  label="Resource-set revision"
                  value={record.resourcesRevision}
                />
              </Stack>
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>
        <RecordActions
          actions={entity.actions.filter(
            (action) => action.name === "delete_record",
          )}
          values={entity.properties}
          primary=""
          root={this.props.root}
          onFollow={this.props.onFollow}
          onRefresh={this.props.onRefresh}
          danger
          collection="records"
        />
        {this.state.editing &&
        edit.kind === "available" &&
        target.kind === "available" ? (
          <RecordEditor
            action={edit.value}
            source={target}
            root={this.props.root}
            onLoad={this.props.onLoad}
            onClose={() => this.setState({ editing: false })}
            onSaved={(saved) =>
              this.setState({
                editing: false,
                saved: { kind: "available", value: saved },
              })
            }
          />
        ) : (
          <></>
        )}
      </ResourcePage>
    );
  }
}

export function RecordDetail(props: SirenEntityProps): ReactNode {
  return (
    <RecordBoundary entity={props.entity} onRefresh={props.onRefresh}>
      <RecordDetailView {...props} />
    </RecordBoundary>
  );
}
