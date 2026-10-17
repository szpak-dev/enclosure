# Check project health

Resolve the exact workspace, then call `check_project_health` with the returned
project and workspace identifiers.

The summary reports configured check counts, failures, advisories, and a bounded
set of links. Use `read_project_health_findings` to page through either finding
kind and `read_project_health_attestation` to inspect the exact conformance inputs
and digests.

Project health is deliberately capacity bounded:

- a request fails immediately with HTTP 503 when every execution slot is busy;
- worker startup has its own timeout;
- the complete execution has a separate timeout;
- a disconnected client cancels work sooner;
- failed, cancelled, and timed-out results are not cached.

Retry only after distinguishing capacity from a deterministic finding. A green
report means the configured checks passed for the attested revisions. It does not
replace tests, design acceptance, implementation acceptance, or release evidence.
