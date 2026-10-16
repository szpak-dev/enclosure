import {
  Alert,
  Button,
  Divider,
  Drawer,
  Group,
  Menu,
  Modal,
  Stack,
  Text,
} from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import type { Action, Entity } from "@siren-js/client";
import { useState } from "react";
import { SirenResponseError } from "../../client/SirenClient";
import type { ActionExecutionResult } from "../../app/useSirenBrowser";
import { SirenDrawerActionForm } from "../siren/SirenActionForm";
import { useSirenActionExecution } from "../siren/SirenActionExecution";
import { ProjectActionResult } from "./ProjectActionResult";

type ActionSelection =
  | { kind: "none" }
  | { kind: "confirm"; action: Action }
  | { kind: "drawer"; action: Action };

type ActionResult =
  | { kind: "idle" }
  | { kind: "empty" }
  | { kind: "entity"; entity: Entity }
  | { kind: "conflict"; entity: Entity };

export type ProjectActionsProps = {
  actions: readonly Action[];
  dangerNames: readonly string[];
  omitNames: readonly string[];
  onRefresh: () => void;
  primaryName: string;
  values: object;
};

export function ProjectActions({
  actions,
  dangerNames,
  omitNames,
  onRefresh,
  primaryName,
  values,
}: ProjectActionsProps) {
  const execution = useSirenActionExecution();
  const narrow = useMediaQuery("(max-width: 48em)") === true;
  const [selection, setSelection] = useState<ActionSelection>({ kind: "none" });
  const [result, setResult] = useState<ActionResult>({ kind: "idle" });
  const visible = actions.filter((action) => !omitNames.includes(action.name));
  const primary = visible.find((action) => action.name === primaryName);
  const secondary = visible.filter(
    (action) => action !== primary && !dangerNames.includes(action.name),
  );
  const danger = visible.filter((action) => dangerNames.includes(action.name));

  const choose = (action: Action) => {
    setResult({ kind: "idle" });
    setSelection(
      dangerNames.includes(action.name)
        ? { kind: "confirm", action }
        : { kind: "drawer", action },
    );
  };
  const close = () => {
    setSelection({ kind: "none" });
    setResult({ kind: "idle" });
  };

  if (!visible.length) return null;

  return (
    <>
      <Stack gap="md">
        <Group>
          {primary ? (
            <Button onClick={() => choose(primary)}>{primary.title}</Button>
          ) : null}
          {secondary.length ? (
            <Menu
              position="bottom-end"
              shadow="md"
              transitionProps={{ duration: 0 }}
              width={280}
            >
              <Menu.Target>
                <Button variant="default">More actions</Button>
              </Menu.Target>
              <Menu.Dropdown>
                {secondary.map((action) => (
                  <Menu.Item key={action.name} onClick={() => choose(action)}>
                    {action.title}
                  </Menu.Item>
                ))}
              </Menu.Dropdown>
            </Menu>
          ) : null}
        </Group>
        {danger.length ? (
          <Stack gap="xs">
            <Divider color="red" label="Danger zone" labelPosition="left" />
            <Group>
              {danger.map((action) => (
                <Button
                  color="red"
                  key={action.name}
                  onClick={() => choose(action)}
                  variant="light"
                >
                  {action.title}
                </Button>
              ))}
            </Group>
          </Stack>
        ) : null}
      </Stack>
      <Modal
        closeButtonProps={{ "aria-label": "Close confirmation" }}
        onClose={close}
        opened={selection.kind === "confirm"}
        title="Confirm destructive action"
        transitionProps={{ duration: 0 }}
      >
        <Stack>
          <Text>
            This operation can remove project configuration. Review the revision
            field before continuing.
          </Text>
          <Group justify="flex-end">
            <Button onClick={close} variant="default">
              Cancel
            </Button>
            {selection.kind === "confirm" ? (
              <Button
                color="red.9"
                onClick={() =>
                  setSelection({ kind: "drawer", action: selection.action })
                }
              >
                Continue
              </Button>
            ) : null}
          </Group>
        </Stack>
      </Modal>
      {selection.kind === "drawer" ? (
        <Drawer
          closeButtonProps={{ "aria-label": "Close action" }}
          onClose={close}
          opened
          position="right"
          size={narrow ? "100%" : "xl"}
          title={selection.action.title}
        >
          <Stack gap="xl">
            {execution.kind === "unavailable" ? (
              <Alert
                color="red"
                role="alert"
                title="Action unavailable"
                variant="outline"
              >
                This surface does not have an action executor.
              </Alert>
            ) : (
              <SirenDrawerActionForm
                action={selection.action}
                onSubmit={async (action, submittedValues) => {
                  let response: ActionExecutionResult;
                  try {
                    response = await execution.execute(action, submittedValues);
                  } catch (reason) {
                    if (
                      reason instanceof SirenResponseError &&
                      action.name ===
                        "get_project_operating_contract_binding" &&
                      reason.status === 409 &&
                      reason.entity
                    ) {
                      setResult({ kind: "conflict", entity: reason.entity });
                      return;
                    }
                    throw reason;
                  }
                  if (response.kind === "empty") {
                    setResult({ kind: "empty" });
                  } else {
                    setResult({ kind: "entity", entity: response.entity });
                  }
                  if (action.method !== "GET" && action.method !== "DELETE")
                    onRefresh();
                }}
                values={values}
              />
            )}
            {result.kind === "empty" ? (
              <Alert
                color="teal.9"
                role="status"
                title="Action completed"
                variant="outline"
              >
                The server completed the action without returning a document.
              </Alert>
            ) : null}
            {result.kind === "entity" ? (
              <Stack>
                <Alert
                  color="teal.9"
                  role="status"
                  title="Action completed"
                  variant="outline"
                >
                  The server returned the result below.
                </Alert>
                <ProjectActionResult
                  actionName={selection.action.name}
                  entity={result.entity}
                />
              </Stack>
            ) : null}
            {result.kind === "conflict" ? (
              <Stack>
                <Alert
                  color="orange.9"
                  role="alert"
                  title="Conflict"
                  variant="outline"
                >
                  The operating contract is not configured for this project.
                  Review the returned evidence before choosing a replacement.
                </Alert>
                <ProjectActionResult
                  actionName={selection.action.name}
                  entity={result.entity}
                />
              </Stack>
            ) : null}
          </Stack>
        </Drawer>
      ) : null}
    </>
  );
}
