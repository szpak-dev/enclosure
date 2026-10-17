# Architecture as an executable promise

An architecture diagram becomes decorative when nothing can distinguish an
implementation that keeps it from one that quietly abandons it.

Mermaiden gives Enclosure typed, revisioned diagram snapshots. An accepted
architecture publication assigns diagram roles to covered units and records
explicit exclusions. Enclosure compiles that intent into a language-neutral
expected implementation manifest.

Modwire observes the source tree, identities, dependencies, flows, cycles,
re-entry, and configured shape. Enclosure compares the implementation document
with the expected manifest and records digest-backed evidence in project health.

The comparison is deliberately bounded. Enclosure does not infer authoritative
intent from arbitrary code, and it does not claim that every UML idea is
executable. It verifies the facts represented by the accepted contract and the
configured analyzers.

A violation is therefore neither an aesthetic disagreement nor a model's opinion.
It is a declared promise that the observed implementation did not keep.
