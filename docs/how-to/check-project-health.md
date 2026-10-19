# Check project health

Resolve the exact workspace, then call `check_project_health` with the returned
project and workspace identifiers.

The summary reports configured check counts, failures, advisories, and a bounded
set of links. Use `read_project_health_findings` to page through either finding
kind and `read_project_health_attestation` to inspect the exact conformance inputs
and digests. Those follow-up operations re-evaluate current project health,
normally reusing exact architecture-stage cache entries, and then require the
resulting revision to match `expected_revision`; they do not read a persisted
prior report.

Project health is deliberately capacity bounded:

- a request fails immediately with HTTP 503 when every execution slot is busy;
- the architecture worker has one overall deadline covering bootstrap and
  evaluation, with an additional bootstrap cap inside that deadline;
- guidance checks, summarization, and final input verification run afterward
  outside the architecture-worker deadline;
- a disconnected client cancels the active worker sooner;
- failed, cancelled, and timed-out architecture-worker evaluations do not commit
  their deferred stage-cache writes.

Retry only after distinguishing capacity from a deterministic finding. A green
report means the configured checks passed for the attested revisions. It does not
replace tests, design acceptance, implementation acceptance, or release evidence.
