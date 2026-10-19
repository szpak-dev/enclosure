# Manage architecture contracts

Enclosure treats accepted diagrams as architectural intent and Modwire output as
implementation evidence. Do not infer intended architecture from whichever code
happens to exist today.

1. Build a tree diagram and at least one owning UML diagram in one diagram set.
   Add mutually consistent entity diagrams when persistence relationships are
   part of the accepted contract.
2. Resolve every blocking diagram constraint and read back the exact snapshots.
3. Publish an architecture contract that names the covered units, diagram roles,
   and any explicit exclusions.
4. Accept the immutable publication through the project's governed workflow.
5. Compile the publication into the expected implementation manifest.
6. Compare a Modwire implementation manifest against that expected contract.
7. Run project health to record conformance together with boundary, flow, shape,
   cycle, re-entry, and guidance findings.

Changing a diagram draft does not rewrite an accepted publication. Publish a new
contract revision when architectural intent changes, and identify the migration
impact before implementation follows it.

The architecture documentation in this repository explains the current accepted
system. It does not become a second architecture source of truth.
