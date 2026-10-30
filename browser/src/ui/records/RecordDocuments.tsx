import {
  Accordion,
  Alert,
  Button,
  Code,
  Group,
  List,
  Stack,
  Text,
} from "@mantine/core";
import type { ReactNode } from "react";
import { Identity, ResourcePage } from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenContinuation } from "../siren/SirenContinuation";
import { recordContract as contract } from "./RecordContract";
import { RecordBoundary, RecordContent } from "./RecordPrimitives";

function RecordDocumentView(props: SirenEntityProps): ReactNode {
  const data = contract.object(props.entity.properties);
  const content = contract.string(data.content);
  const offset = contract.number(data.offset);
  const total = contract.number(data.total_characters);
  const revision = contract.string(data.revision);
  const source = Object.hasOwn(data, "path");
  const schema = Object.hasOwn(data, "category_id");
  const title = source
    ? contract.string(data.path)
    : schema
      ? `Category schema v${contract.number(data.schema_version)}`
      : "Record source";
  const complete =
    !source &&
    offset === 0 &&
    Array.from(content).length === total &&
    data.has_more === false;
  return (
    <ResourcePage
      title={title}
      description={
        source
          ? "Attached source resource."
          : schema
            ? "Versioned category content contract."
            : "Revision-pinned record content."
      }
    >
      <Text>
        Characters {offset}–{offset + Array.from(content).length} of {total}
      </Text>
      {source ? (
        <Text c="dimmed">
          {contract.string(data.language)} · {contract.string(data.media_type)}
        </Text>
      ) : (
        <></>
      )}
      {complete ? (
        <RecordContent value={contract.parseContent(content)} />
      ) : (
        <>
          <Alert title={source ? "Source text" : "Source page"}>
            {source
              ? "Use the page controls to read the remaining source."
              : "This is a partial JSON document. Page controls preserve its revision."}
          </Alert>
          <Code block>{content}</Code>
        </>
      )}
      <SirenContinuation entity={props.entity} onFollow={props.onFollow} />
      <Accordion>
        <Accordion.Item value="revision">
          <Accordion.Control>Revision</Accordion.Control>
          <Accordion.Panel>
            <Identity label="Document revision" value={revision} />
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </ResourcePage>
  );
}

export function RecordDocument(props: SirenEntityProps): ReactNode {
  return (
    <RecordBoundary entity={props.entity} onRefresh={props.onRefresh}>
      <RecordDocumentView {...props} />
    </RecordBoundary>
  );
}

function ResourceManifestView(props: SirenEntityProps): ReactNode {
  return (
    <ResourcePage
      title="Record resources"
      description="Source attachments and their revision-pinned content."
    >
      {props.entity.entities.length ? (
        <List
          listStyleType="none"
          spacing="md"
          styles={{
            itemWrapper: { width: "100%" },
            itemLabel: { width: "100%" },
          }}
        >
          {props.entity.entities.map((item) => {
            const manifest = contract.manifest(contract.properties(item));
            const target = contract.target(item);
            return (
              <List.Item key={manifest.path}>
                <Group justify="space-between" wrap="nowrap" w="100%">
                  <Stack gap={4} miw={0}>
                    <Text fw={600} style={{ overflowWrap: "anywhere" }}>
                      {manifest.path}
                    </Text>
                    <Text c="dimmed" size="sm">
                      {manifest.language} · {manifest.mediaType} ·{" "}
                      {manifest.size} bytes
                    </Text>
                    <Accordion>
                      <Accordion.Item value="revision">
                        <Accordion.Control>Revision</Accordion.Control>
                        <Accordion.Panel>
                          <Identity
                            label="Resource revision"
                            value={manifest.revision}
                          />
                        </Accordion.Panel>
                      </Accordion.Item>
                    </Accordion>
                  </Stack>
                  {target.kind === "available" ? (
                    <Button
                      variant="light"
                      aria-label={`Open ${manifest.path}`}
                      onClick={() =>
                        props.onFollow(
                          contract.query(target.value, {
                            expected_revision: manifest.revision,
                            path: manifest.path,
                            offset: 0,
                            limit: 10000,
                          }),
                        )
                      }
                    >
                      Open
                    </Button>
                  ) : (
                    <Text>Content unavailable</Text>
                  )}
                </Group>
              </List.Item>
            );
          })}
        </List>
      ) : (
        <Alert title="No resources attached">
          This record has no source attachments.
        </Alert>
      )}
      <SirenContinuation entity={props.entity} onFollow={props.onFollow} />
    </ResourcePage>
  );
}

export function RecordResourceManifests(props: SirenEntityProps): ReactNode {
  return (
    <RecordBoundary entity={props.entity} onRefresh={props.onRefresh}>
      <ResourceManifestView {...props} />
    </RecordBoundary>
  );
}
