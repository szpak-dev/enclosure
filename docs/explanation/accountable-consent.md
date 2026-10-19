# Accountable consent

Code generation changes the cost of production. It does not remove the need to
know why a change was allowed, which rules applied, what evidence was examined,
and who accepted the result.

**Progress without accountable consent is not progress.**

That principle is stricter than keeping an audit log. A log can prove that a
request happened while saying nothing about whether the actor had the right
context, whether the architecture still matched the accepted design, or whether
the final evidence was reviewed by the person responsible for the system.

The Enclosure runtime and its repository workflow keep those concerns distinct:

- guidance establishes what applies to the task;
- accepted diagrams and architecture configurations establish intended structure;
- Modwire and conformance checks produce implementation evidence;
- security identifies the actor and classifies the operation;
- repository agent instructions require explicit human phase decisions and the
  repository workflow is responsible for capturing them.

Enclosure persists operation audit events and destructive-approval state. It
returns context receipts and keeps successful architecture-evaluation stages,
including architecture findings and attestations, in a bounded, evictable
filesystem cache for reuse. The combined project-health report is rebuilt with
current guidance checks and final input verification; it is not a durable
evidence record. Enclosure does not currently persist a typed design-,
implementation-, verification-, or delivery-acceptance artifact, nor does it
verify that a repository captured those decisions. Those phase decisions belong
to the workflow that consumes Enclosure's evidence.

The product does not make an agent morally responsible. It makes authority and
evidence difficult to lose in the speed of the work.
