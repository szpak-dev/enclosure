from collections.abc import Mapping

from django.db import migrations
from mermaiden import Application


def upgrade_snapshots(apps, schema_editor) -> None:
    diagram_model = apps.get_model("diagrams", "Diagram")
    database = schema_editor.connection.alias
    application = Application.create()
    try:
        for stored in diagram_model.objects.using(database).order_by("id").iterator():
            snapshot = stored.snapshot
            if not isinstance(snapshot, Mapping):
                raise RuntimeError(f"Diagram {stored.pk!s} snapshot must be an object.")
            if snapshot.get("version") != 6:
                raise RuntimeError(
                    f"Diagram {stored.pk!s} has unsupported Mermaiden snapshot version "
                    f"{snapshot.get('version')!r}; expected version 6."
                )
            candidate = {**snapshot, "version": 7}
            diagram = application.restore(candidate)
            canonical = application.snapshot(diagram).to_dict()
            if canonical != candidate:
                raise RuntimeError(f"Diagram {stored.pk!s} snapshot is not canonical under Mermaiden 11.")
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
        ("diagrams", "0003_upgrade_mermaiden_snapshots"),
    ]

    operations = [
        migrations.RunPython(upgrade_snapshots),
    ]
