import type { Action } from "@siren-js/client";
import { SirenResponseError } from "../../client/SirenClient";
import {
  ResourceActions,
  type ResourceActionErrorResolution,
} from "../resource/ResourceActions";
import { ProjectActionResult } from "./ProjectActionResult";

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
  return (
    <ResourceActions
      actions={actions}
      dangerDescription="This operation can remove project configuration. Review the revision field before continuing."
      dangerNames={dangerNames}
      omitNames={omitNames}
      onCompleted={(action) => {
        if (action.method !== "GET" && action.method !== "DELETE") onRefresh();
      }}
      primaryName={primaryName}
      renderResult={({ actionName, entity }) => (
        <ProjectActionResult actionName={actionName} entity={entity} />
      )}
      resolveError={(action, reason): ResourceActionErrorResolution => {
        if (
          reason instanceof SirenResponseError &&
          action.name === "get_project_operating_contract_binding" &&
          reason.status === 409 &&
          reason.entity
        )
          return {
            kind: "conflict",
            conflict: {
              description:
                "The operating contract is not configured for this project. Review the returned evidence before choosing a replacement.",
              entity: reason.entity,
              title: "Conflict",
            },
          };
        return { kind: "unhandled" };
      }}
      values={values}
    />
  );
}
