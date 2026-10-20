from collections.abc import Mapping

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from mermaiden import Application


def upgrade_snapshots(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    diagram_model = apps.get_model("diagrams", "Diagram")
    database = schema_editor.connection.alias
    application = Application.create()
    try:
        for stored in diagram_model.objects.using(database).order_by("id").iterator():
            snapshot = stored.snapshot
            if not isinstance(snapshot, Mapping):
                raise RuntimeError(f"Diagram {stored.pk!s} snapshot must be an object.")
            if snapshot.get("version") != 7:
                raise RuntimeError(
                    f"Diagram {stored.pk!s} has unsupported Mermaiden snapshot version "
                    f"{snapshot.get('version')!r}; expected version 7."
                )
            if snapshot.get("kind") != stored.kind:
                raise RuntimeError(
                    f"Diagram {stored.pk!s} kind mismatch: record has {stored.kind!r}, "
                    f"snapshot has {snapshot.get('kind')!r}."
                )
            configuration = snapshot.get("configuration")
            if not isinstance(configuration, Mapping):
                raise RuntimeError(f"Diagram {stored.pk!s} configuration must be an object.")
            fields = configuration.get("fields")
            if not isinstance(fields, Mapping):
                raise RuntimeError(f"Diagram {stored.pk!s} configuration fields must be an object.")

            current = application.snapshot(application.create_diagram(stored.kind)).to_dict()
            current_configuration = current["configuration"]
            if configuration.get("$type") != current_configuration["$type"]:
                raise RuntimeError(f"Diagram {stored.pk!s} configuration type is not supported by Mermaiden 11.0.1.")
            candidate = {
                **snapshot,
                "version": 8,
                "configuration": {
                    **configuration,
                    "fields": {
                        **current_configuration["fields"],
                        **fields,
                    },
                },
            }
            diagram = application.restore(candidate)
            canonical = application.snapshot(diagram).to_dict()
            if canonical["kind"] != stored.kind:
                raise RuntimeError(
                    f"Diagram {stored.pk!s} kind mismatch: record has {stored.kind!r}, "
                    f"snapshot has {canonical['kind']!r}."
                )
            source = "" if canonical["draft"] is True else application.render(diagram)
            diagram_model.objects.using(database).filter(pk=stored.pk).update(
                snapshot=canonical,
                source=source,
            )
    finally:
        application.close()


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("diagrams", "0004_upgrade_mermaiden_11_snapshots"),
    ]

    operations = [
        migrations.RunPython(upgrade_snapshots),
    ]
