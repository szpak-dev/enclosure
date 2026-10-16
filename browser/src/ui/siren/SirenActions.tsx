import { Stack } from "@mantine/core";
import type { Action } from "@siren-js/client";
import { sirenRegistry } from "./SirenRegistry";
import { SirenActionForm } from "./SirenActionForm";

export type SirenActionsProps = {
  actions: Action[];
  onSubmit: (action: Action, values: Record<string, unknown>) => void;
  values?: object;
};

export function SirenActions({ actions, onSubmit, values }: SirenActionsProps) {
  if (!actions.length) return null;

  return (
    <Stack>
      {actions.map((action) => {
        const ActionForm =
          sirenRegistry.actions.get(action.name) ?? SirenActionForm;
        return (
          <ActionForm
            action={action}
            key={`${action.method}-${action.href}-${action.name}`}
            onSubmit={onSubmit}
            {...(values ? { values } : {})}
          />
        );
      })}
    </Stack>
  );
}
