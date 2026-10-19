# Manage scaffoldings

Scaffoldings hold revisioned source templates and typed rendering variables.

1. Create a scaffolding with its language, purpose, variables, template paths,
   bodies, and write modes.
2. Read the compact scaffolding and its revision-pinned template manifest.
3. Render with explicit values for every required variable.
4. Page through rendered-file manifests and inspect exact file content before
   writing anything into a workspace.
5. Use `generate_project_source` only through the registered project and workspace
   that own the destination.

`create_if_missing` protects existing files. `overwrite` is appropriate only when
the template is the accepted owner of the destination. Rendering is a preview;
workspace generation is the mutation.

Deleting a scaffolding permanently removes its templates and requires one-time
destructive approval.
