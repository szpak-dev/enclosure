# Manage guidance and operating contracts

Guidance starts as a record. An operating contract publishes an immutable ordered
set of mandatory guidance references, and a project binding selects the effective
contract revision.

1. Create record tags and a category whose JSON Schema owns the content shape.
2. Create the guidance records with provenance-bearing resources where needed.
3. Create an operating contract with a stable authority.
4. Publish a revision containing at least one mandatory guidance reference.
5. Bind the project to that exact version with either `pinned` or `follow-latest`.
6. Add eligible optional records through `replace_guidance_scopes`.
7. Describe prerequisites, containment, refinement, and escalation through
   `replace_guidance_relationships`.
8. Call `get_workspace_context` with representative tasks and inspect the receipt.

Replacing scopes or relationships replaces the complete project collection. Read
the current collection first and submit the intended complete result. A record
referenced by a published operating contract cannot be deleted.

Use `pinned` when a project must remain on one reviewed revision. Use
`follow-latest` only when the contract owner and project have agreed that later
publications become effective without replacing the binding.
