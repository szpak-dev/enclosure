# Operate the machine-wide MCP server

The Compose runtime keeps one Enclosure MCP server available to local projects at
`http://127.0.0.1:8666/mcp`.

## Configure the runtime

Create `.env` with an exact released image and the database connection required by
the Compose environment:

```text
ENCLOSURE_IMAGE=szpak/enclosure:v1.21.1
ENCLOSURE_PROJECTS_DIR=/absolute/path/to/projects
DATABASE_URL=postgres://user:password@resumed-db:5432/enclosure
SECRET_KEY=replace-me
```

Use an immutable SemVer tag for `ENCLOSURE_IMAGE`. The moving `latest` tag cannot
identify the implementation that produced an architecture attestation.

`ENCLOSURE_PROJECTS_DIR` is mounted into the container at the same absolute path.
Workspace bindings therefore resolve to the same path on the host and in the
runtime.

## Start or update

```console
make runtime-config
make runtime-up
curl --fail http://127.0.0.1:8666/health/
```

`runtime-up` pulls the configured image, retains the prior image as `:previous`,
runs migrations with the selected image, and then recreates the MCP service.
Back up PostgreSQL before deploying a release with potentially irreversible
migrations.

## Recover or stop

```console
make runtime-rollback
make runtime-down
```

Rollback uses the locally retained `:previous` image and runs its migrations
before recreating the service. `runtime-down` removes the MCP container but keeps
the named health and Modwire cache volumes.

See [configuration](../reference/configuration.md) for every runtime variable and
default.
