import type { Entity } from "@siren-js/client";
import { ResourceActions } from "../resource/ResourceActions";
import { ResourcePage, Section } from "../resource/ResourcePrimitives";
import type { SirenEntityProps } from "../siren/SirenEntity";
import { SirenContinuation } from "../siren/SirenContinuation";
import { ScaffoldingActionResult } from "./ScaffoldingActionResult";
import { ScaffoldingCards } from "./ScaffoldingCards";

export function ScaffoldingCollection({
  entity,
  onFollow,
  onRefresh,
}: SirenEntityProps) {
  const searchResults = entity.class.includes("name-search-result");
  const title = searchResults ? "Scaffolding search results" : "Scaffoldings";
  return (
    <ResourcePage
      description={
        searchResults
          ? "Scaffolding references matching the submitted name and language filters."
          : "Reusable source templates and the inputs used to render them."
      }
      title={title}
    >
      <ResourceActions
        actions={entity.actions}
        dangerDescription="This action does not remove scaffolding data."
        dangerNames={[]}
        omitNames={["find_scaffoldings"]}
        onCompleted={(action) => {
          if (action.name === "create_scaffolding") onRefresh();
        }}
        primaryName={
          searchResults ? "search_scaffoldings" : "create_scaffolding"
        }
        renderResult={({ actionName, entity: result, values }) => (
          <ScaffoldingActionResult
            actionName={actionName}
            entity={result}
            onFollow={onFollow}
            values={values}
          />
        )}
        resolveError={() => ({ kind: "unhandled" })}
        values={entity.properties}
      />
      <Section title={searchResults ? "Matches" : "Available scaffoldings"}>
        <ScaffoldingCards items={entity.entities} onFollow={onFollow} />
        <SirenContinuation entity={entity} onFollow={onFollow} />
      </Section>
    </ResourcePage>
  );
}

export function isScaffoldingSearchResult(entity: Entity): boolean {
  return (
    entity.class.includes("collection") &&
    entity.class.includes("name-search-result") &&
    entity.title === "ScaffoldingSummary"
  );
}
