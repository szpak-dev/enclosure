# Errors and limits

REST errors use operation-specific JSON objects. Parsing and common resource
errors include `detail`; security and state responses expose the stable fields
needed to continue or diagnose their particular decision.

| Status | Meaning |
| --- | --- |
| 400 | The request body or transport input could not be parsed. |
| 401 | Credentials are missing or invalid; `reason_code` identifies the authentication failure. |
| 403 | The actor lacks permission; the response includes `execution_id` and `reason_code`. |
| 404 | The addressed resource does not exist. |
| 409 | Current state conflicts with the operation, or a destructive action requires one-time approval. An unconfigured operating-contract response instead identifies its `state` and `project_id`. |
| 422 | Request-schema validation or a validly shaped request's domain validation failed. |
| 500 | Internal execution failed or an operation has no security policy. |
| 503 | Project-health execution capacity is unavailable. |
| 504 | Project-health execution exceeded its timeout. |

A destructive-approval response includes `approval_request_id`, `execution_id`,
`reason_code`, and `expires_at`. Approving the request does not execute the
operation; the caller must retry the exact operation before expiry.

Collection and content operations are bounded. Follow `next` links or use the
returned offset and limit instead of requesting an unbounded catalog. Revision-
pinned content reads fail rather than combining stale and current state.
