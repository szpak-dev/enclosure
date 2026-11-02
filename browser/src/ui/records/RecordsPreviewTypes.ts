export type PreviewState =
  | "normal"
  | "empty"
  | "historical"
  | "load-failure"
  | "loading"
  | "stale"
  | "protected"
  | "approval"
  | "search-empty"
  | "search-failure"
  | "save-failure"
  | "delete-success";
export type PreviewProps = {
  initial:
    | "records"
    | "record"
    | "categories"
    | "category"
    | "tags"
    | "tag"
    | "resources"
    | "source"
    | "editor"
    | "new";
  scenario: PreviewState;
};
