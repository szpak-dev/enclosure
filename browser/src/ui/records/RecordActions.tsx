import { Alert, Button, Group, Stack } from "@mantine/core";
import type { Action, Entity, Target } from "@siren-js/client";
import { Component, type ReactNode } from "react";
import { SirenResponseError } from "../../client/SirenError";
import {
  ResourceActions,
  type ResourceActionErrorResolution,
} from "../resource/ResourceActions";
import { recordContract as contract } from "./RecordContract";
import { RecordValue } from "./RecordPrimitives";

type ActionsProps = {
  actions: readonly Action[];
  values: object;
  primary: string;
  root: Entity;
  onFollow: (target: Target) => void;
  onRefresh: () => void;
  danger: boolean;
  collection: "records" | "categories" | "tags";
};

export class RecordActions extends Component<ActionsProps> {
  private resolve(reason: unknown): ResourceActionErrorResolution {
    if (!(reason instanceof SirenResponseError) || !reason.entity)
      return { kind: "unhandled" };
    const data = contract.object(reason.entity.properties);
    if (data.reason_code === "destructive_approval_required")
      return {
        kind: "conflict",
        conflict: {
          title: "One-time approval required",
          description:
            "Deletion has not run. An authorized security client must approve the exact request below. Then retry Delete before the approval expires.",
          entity: reason.entity,
        },
      };
    if (reason.status === 409 || reason.status === 422)
      return {
        kind: "conflict",
        conflict: {
          title: "Action could not proceed",
          description: reason.message,
          entity: reason.entity,
        },
      };
    return { kind: "unhandled" };
  }

  private completed(action: Action): void {
    if (action.method === "DELETE") {
      const target = contract.collection(
        this.props.root,
        this.props.collection,
      );
      if (target.kind === "available") this.props.onFollow(target.value);
    }
  }

  private result(entity: Entity): ReactNode {
    const data = contract.object(entity.properties);
    const schemaReceipt =
      Object.hasOwn(data, "category_id") && Object.hasOwn(data, "version");
    return (
      <Stack>
        {schemaReceipt ? (
          <Alert
            color="teal.9"
            variant="filled"
            autoContrast
            title={`Schema v${contract.number(data.version)} saved`}
          >
            Existing records keep their assigned schema version.
          </Alert>
        ) : (
          <></>
        )}
        <RecordValue value={contract.jsonObject(data)} />
        <Group>
          <Button onClick={this.props.onRefresh}>Refresh view</Button>
          {entity.links
            .filter((link) => !link.rel.includes("self"))
            .map((link) => (
              <Button
                key={contract.href(link)}
                variant="light"
                onClick={() =>
                  this.props.onFollow(
                    schemaReceipt &&
                      new URL(
                        contract.href(link),
                        window.location.origin,
                      ).pathname.endsWith("/content-schema")
                      ? contract.query(link, {
                          expected_revision: contract.string(data.revision),
                          schema_version: contract.number(data.version),
                          offset: 0,
                          limit: 10000,
                        })
                      : link,
                  )
                }
              >
                {link.title || "Open result"}
              </Button>
            ))}
        </Group>
      </Stack>
    );
  }

  render(): ReactNode {
    const dangerNames = [
      "delete_record",
      "delete_record_category",
      "delete_record_tag",
    ];
    return (
      <ResourceActions
        actions={this.props.actions}
        values={this.props.values}
        primaryName={this.props.primary}
        scope={this.props.danger ? "danger" : "safe"}
        dangerNames={dangerNames}
        omitNames={[]}
        dangerDescription={
          this.props.collection === "records"
            ? "Deletion permanently removes this record and its source resources. Published or protected records cannot be deleted."
            : "Only unused categories and tags can be deleted."
        }
        onCompleted={(action) => this.completed(action)}
        renderResult={({ entity }) => this.result(entity)}
        resolveError={(_, reason) => this.resolve(reason)}
      />
    );
  }
}
