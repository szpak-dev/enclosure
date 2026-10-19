# The governed delivery loop

A coding task crosses several authorities. Treating them as one prompt hides the
moment at which intent becomes implementation and implementation becomes evidence.

The documented operating model keeps the sequence explicit across Enclosure and
the repository workflow that consumes it:

1. **Intent** — people accept the relevant requirements and diagrams through the
   repository workflow.
2. **Context** — Enclosure selects applicable guidance for the registered
   workspace and task.
3. **Change** — the agent works inside those constraints on an issue branch.
4. **Verification** — tests and Enclosure project health evaluate observable
   behavior and architecture against exact inputs.
5. **Evidence** — Enclosure findings and attestations identify what was checked.
6. **Acceptance** — a human decides in the repository workflow whether the
   implementation is ready to move.
7. **Delivery** — issue, pull-request, and board state record what shipped.

Each boundary matters because a later green signal cannot retroactively create an
earlier decision. Passing tests do not accept a design. A valid architecture
attestation does not merge a pull request. An agent completing a tool call does
not authorize the next phase.

Enclosure persists accepted architectural intent and operating-contract
revisions. It does not persist the repository's decisions to begin implementation,
accept verification, or authorize delivery, and it does not verify that those
decisions were captured. Agent instructions state the policy; repository state
must carry its execution. The loop is useful precisely because it refuses to turn
confidence into authority.
