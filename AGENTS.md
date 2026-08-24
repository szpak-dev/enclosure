At the first task in a workspace, call get_workspace_context(root, task) once.
Treat returned guidance as policy. Do not inspect the API root, list all projects,
or search all records unless workspace context is unavailable.

Check project health after structural source, public API, DI, or architecture-rule
changes. A test-only change does not require health unless it changes architectural coverage.

After an ambiguous mutating-tool failure, verify state before retrying.
Read-only failures may use the documented fallback directly.