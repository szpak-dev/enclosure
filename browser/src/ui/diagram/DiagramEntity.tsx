import { Code, Paper, Stack, Tabs, Title } from "@mantine/core";
import type { Entity } from "@siren-js/client";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenActions } from "../siren/SirenActions";
import { SirenProperties } from "../siren/SirenProperties";
import { SirenValue } from "../siren/SirenValue";
import {
  DiagramCommandForm,
  isDiagramCommandAction,
} from "./DiagramCommandForm";
import { DiagramRenderer } from "./DiagramRenderer";

export type DiagramProperties = Entity["properties"] & {
  id: string;
  kind: string;
  revision: number;
  snapshot: unknown;
  source: string;
  title: string;
};

export function DiagramEntity({
  entity,
  onLoad,
  onRefresh,
  onSubmit,
  root,
}: SirenEntityProps) {
  const properties = entity.properties as DiagramProperties;
  const commandAction = entity.actions.find(isDiagramCommandAction);
  const remainingActions = entity.actions.filter(
    (action) => action !== commandAction,
  );

  return (
    <Paper component="article" aria-label={properties.title} p="md" shadow="xs">
      <Stack>
        <Title order={1}>{properties.title}</Title>
        <Tabs defaultValue="diagram" keepMounted={false}>
          <Tabs.List>
            <Tabs.Tab value="diagram">Diagram</Tabs.Tab>
            <Tabs.Tab value="source">Source</Tabs.Tab>
            <Tabs.Tab value="snapshot">Snapshot</Tabs.Tab>
            <Tabs.Tab value="metadata">Metadata</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel pt="md" value="diagram">
            <DiagramRenderer
              diagramId={properties.id}
              revision={properties.revision}
              source={properties.source}
            />
          </Tabs.Panel>
          <Tabs.Panel pt="md" value="source">
            <Code
              block
              mah="36rem"
              style={{ overflow: "auto", whiteSpace: "pre" }}
            >
              {properties.source}
            </Code>
          </Tabs.Panel>
          <Tabs.Panel pt="md" value="snapshot">
            <SirenValue value={properties.snapshot} />
          </Tabs.Panel>
          <Tabs.Panel pt="md" value="metadata">
            <SirenProperties entity={entity} exclude={["snapshot", "source"]} />
          </Tabs.Panel>
        </Tabs>
        {commandAction ? (
          <DiagramCommandForm
            action={commandAction}
            kind={properties.kind}
            onLoad={onLoad}
            onRefresh={onRefresh}
            onSubmit={onSubmit}
            revision={properties.revision}
            root={root}
          />
        ) : null}
        <SirenActions
          actions={remainingActions}
          onSubmit={onSubmit}
          values={entity.properties}
        />
      </Stack>
    </Paper>
  );
}
