# Manage diagrams

Discover the runtime diagram catalog before creating a diagram. Each kind exposes
its semantic commands and JSON payload contracts.

1. Create a diagram set for one coherent topic.
2. Create an empty typed diagram or create it from an ordered command batch.
3. Read the diagram kind and command schema before constructing arguments.
4. Apply related commands as one atomic batch when partial success would leave an
   invalid design.
5. Read back both the canonical snapshot and rendered source at the returned
   revision.
6. Resolve every blocking constraint before publication or rendering is treated
   as complete.

Updates use optimistic concurrency. Submit the revision on which the change is
based; do not retry a conflict against a newer diagram without reading and
reconciling that state.

Deleting a diagram or diagram set is destructive and requires one-time approval.
