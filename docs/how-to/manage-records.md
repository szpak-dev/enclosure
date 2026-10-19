# Manage records

Records store typed engineering knowledge together with classification and source
material.

1. Create a tag for each stable classification needed by search or guidance.
2. Create a category with a JSON Schema Draft 2020-12 content contract.
3. Create the record with validated JSON content, tag assignments, and optional
   source resources.
4. Read the compact record first, then follow revision-pinned content and resource
   links for large bodies.
5. Use semantic search when a natural-language task is more useful than category
   or tag enumeration.

Category schema revisions are immutable once referenced. Updating a referenced
schema publishes its next version instead of changing the contract behind existing
records. Read operations are bounded so large guidance bodies do not crowd task
context.

Deleting a record requires destructive permission and one-time approval. Records
published in an operating contract cannot be deleted.
