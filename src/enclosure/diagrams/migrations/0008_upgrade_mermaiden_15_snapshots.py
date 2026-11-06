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
        prefix="0008-mermaiden-15-",
        suffix=".json",
        delete=False,
    ) as backup:
        serializers.serialize("json", diagrams.iterator(), stream=backup)
        backup.flush()
        os.fsync(backup.fileno())

    with Application.create() as application:
        for stored in diagrams.iterator():
            snapshot = deepcopy(stored.snapshot)
            if snapshot["version"] not in {10, 11}:
                raise RuntimeError(
                    f"Diagram {stored.pk!s} has unsupported Mermaiden snapshot version "
                    f"{snapshot['version']!r}; expected version 10 or 11."
                )
            if snapshot["kind"] != stored.kind:
                raise RuntimeError(f"Diagram {stored.pk!s} snapshot kind does not match its record.")

            if stored.kind == "classDiagram":
                snapshot["configuration"]["fields"].pop("html_labels", None)
            if stored.kind == "packet":
                packet = application.create_diagram("packet")
                for element in snapshot["elements"]:
                    fields = element["fields"]
                    if fields["bits"] is not None:
                        if fields["start"] is not None or fields["end"] is not None:
                            raise RuntimeError(f"Diagram {stored.pk!s} has an ambiguous Packet field position.")
                        application.execute(
                            packet,
                            "add_bits",
                            {"id": fields["id"], "label": fields["label"], "bits": fields["bits"]},
                        )
                    else:
                        application.execute(
                            packet,
                            "add_field",
                            {
                                "id": fields["id"],
                                "label": fields["label"],
                                "start": fields["start"],
                                "end": fields["start"] if fields["end"] is None else fields["end"],
                            },
                        )
                converted = application.snapshot(packet).to_dict()["elements"]
                for original, current in zip(snapshot["elements"], converted, strict=True):
                    fields = original["fields"]
                    del fields["start"], fields["end"], fields["bits"]
                    fields["position"] = current["fields"]["position"]
            snapshot["version"] = 12
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
        ("diagrams", "0007_upgrade_mermaiden_14_snapshots"),
    ]

    operations = [
        migrations.RunPython(upgrade_snapshots),
    ]
