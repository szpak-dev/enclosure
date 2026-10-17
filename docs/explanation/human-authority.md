# Human authority and destructive approval

Automation is most dangerous when the ability to call an operation is mistaken
for permission to decide its consequences.

Enclosure classifies public operations as reads, mutations, destructive actions,
approvals, or audit access. It identifies the actor, constructs an operation
intent, checks the required permission, and records the outcome.

Destructive operations use a two-step boundary. The first attempt returns an
exact, expiring approval request. An authorized actor may approve or reject that
request. Approval is consumed once when the matching operation is retried; it is
not a reusable permission slip for a similar payload.

The same principle appears in delivery. Design acceptance, implementation
acceptance, verification acceptance, and merge authority are separate decisions.
Enclosure helps agents carry the evidence between them. It does not collapse them
into one autonomous action.
