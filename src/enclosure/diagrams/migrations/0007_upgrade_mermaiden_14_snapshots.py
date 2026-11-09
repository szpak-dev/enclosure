import os
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.apps.registry import Apps
from django.conf import settings
from django.core import serializers
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.utils import timezone
from mermaiden import Application


def upgrade_snapshots(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    diagram_model = apps.get_model("diagrams", "Diagram")
    database = schema_editor.connection.alias
    diagrams = diagram_model.objects.using(database).select_for_update().order_by("id")
    if not diagrams.exists():
        return

    backup_directory = Path(
        os.environ.get("DIAGRAM_SNAPSHOT_BACKUP_DIRECTORY", str(settings.BASE_DIR / ".dev/backups/diagrams"))
    )
    backup_directory.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=backup_directory,
        prefix="0007-mermaiden-14-",
        suffix=".json",
        delete=False,
    ) as backup:
        serializers.serialize("json", diagrams.iterator(), stream=backup)
        backup.flush()
        os.fsync(backup.fileno())

    with Application.create() as application:
        for stored in diagrams.iterator():
            if application.snapshot_contract_identity(stored.kind).snapshot_version > 10:
                continue
            snapshot = deepcopy(stored.snapshot)
            if snapshot["version"] != 9:
                raise RuntimeError(
                    f"Diagram {stored.pk!s} has unsupported Mermaiden snapshot version "
                    f"{snapshot['version']!r}; expected version 9."
                )
            if snapshot["kind"] != stored.kind:
                raise RuntimeError(f"Diagram {stored.pk!s} snapshot kind does not match its record.")

            snapshot["version"] = 10
            if stored.kind in {"classDiagram", "treeView-beta"}:
                snapshot["annotations"] = []
            diagram = application.restore(snapshot)
            canonical = application.snapshot(diagram).to_dict()
            source = ""
            if not canonical["draft"]:
                report = application.validate_render(diagram)
                if not report.success:
                    diagnostics = "; ".join(
                        f"{diagnostic.code.value}: {diagnostic.message} {diagnostic.details}".strip()
                        for diagnostic in report.diagnostics
                    )
                    raise RuntimeError(f"Diagram {stored.pk!s} failed Mermaiden render validation: {diagnostics}")
                source = application.render(diagram)
            diagram_model.objects.using(database).filter(pk=stored.pk).update(
                snapshot=canonical,
                source=source,
                revision=stored.revision + 1,
                updated_at=timezone.now(),
            )


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("diagrams", "0006_upgrade_mermaiden_13_snapshots"),
    ]

    operations = [
        migrations.RunPython(upgrade_snapshots),
    ]
