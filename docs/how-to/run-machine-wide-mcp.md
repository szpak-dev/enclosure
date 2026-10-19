# Operate the machine-wide MCP server

The repository Compose runtime keeps one Enclosure MCP server available to local
projects at `http://127.0.0.1:8666/mcp`. It is the deployment configuration used
by this checkout, not a standalone public Compose stack.

It requires an existing external Docker network named `resumed-api_default` and
a PostgreSQL server with `pgvector` reachable on that network as `resumed-db`.
Enclosure does not create either dependency. Adapt `compose.yaml` before using it
in an environment that does not provide them.

## Configure the runtime

Create `.env` with an exact released image and the database connection required by
the Compose environment:

```text
ENCLOSURE_IMAGE=docker.io/9orky/enclosure:1.21.1
ENCLOSURE_PROJECTS_DIR=/absolute/path/to/projects
DATABASE_URL=postgres://user:password@resumed-db:5432/enclosure
SECRET_KEY=replace-me
```

Use a version-specific SemVer tag for `ENCLOSURE_IMAGE`; the moving `latest` tag
cannot identify the intended release. Registry tags can be retargeted. The
current `runtime-up` and `runtime-rollback` targets require a tag-form image
reference and do not support digest-pinned references, so record the pulled
digest separately when exact implementation identity matters.

`ENCLOSURE_PROJECTS_DIR` is mounted into the container at the same absolute path.
Workspace bindings therefore resolve to the same path on the host and in the
runtime.

This Compose configuration includes the non-local host `enclosure-mcp`, so MCP
bearer authentication is enabled by default. The repository does not currently
provide a public credential-issuance command, and `compose.yaml` does not expose
the `SECURITY_*` settings for override. A client therefore needs a compatible
bearer token provisioned outside this repository. Use the development runtime for
local unauthenticated evaluation; do not expose that development mode remotely.

## Start or update

```console
make runtime-config
make runtime-up
curl --fail http://127.0.0.1:8666/health/
```

`runtime-up` pulls the configured image, runs migrations with that image, and
then recreates the MCP service. It updates `:previous` only when the same
configured tag already exists locally with a different image digest. Changing
from one version-specific SemVer tag to another does not automatically preserve
the image used by the running container.

Before changing `ENCLOSURE_IMAGE`, explicitly tag the current image when the
deployment needs `runtime-rollback`:

```console
docker image tag docker.io/9orky/enclosure:<current-version> docker.io/9orky/enclosure:previous
```

Confirm that exact `:previous` image exists, and back up PostgreSQL before
deploying a release with potentially irreversible migrations.

## Recover or stop

```console
make runtime-rollback
make runtime-down
```

`runtime-rollback` requires a tag-form `ENCLOSURE_IMAGE` and succeeds only when
the exact repository has a local `:previous` tag. It runs that image's migrations
before recreating the service; it cannot guarantee that a database migrated by a
newer release is backward compatible. `runtime-down` removes the MCP container
but keeps the named health and Modwire cache volumes.

See [configuration](../reference/configuration.md) for every runtime variable and
default.
