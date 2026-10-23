from collections.abc import Mapping

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from mermaiden import Application

LEGACY_RENDERERS = {
    "classDiagram": "mermaiden/enum/classDiagram/class_renderer",
    "flowchart": "mermaiden/enum/flowchart/flowchart_renderer",
    "stateDiagram-v2": "mermaiden/enum/stateDiagram-v2/state_renderer",
}
LAYOUTS = {
    "dagre-d3": "dagre",
    "dagre-wrapper": "dagre",
    "elk": "elk",
}


def upgrade_snapshots(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    diagram_model = apps.get_model("diagrams", "Diagram")
    database = schema_editor.connection.alias
    application = Application.create()
    try:
        for stored in diagram_model.objects.using(database).order_by("id").iterator():
            snapshot = stored.snapshot
            if not isinstance(snapshot, Mapping):
                raise RuntimeError(f"Diagram {stored.pk!s} snapshot must be an object.")
            if snapshot.get("version") not in {7, 8}:
                raise RuntimeError(
                    f"Diagram {stored.pk!s} has unsupported Mermaiden snapshot version "
                    f"{snapshot.get('version')!r}; expected version 7 or 8."
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
                raise RuntimeError(f"Diagram {stored.pk!s} configuration type is not supported by Mermaiden 13.1.0.")
            current_fields = current_configuration["fields"]
            removable = {"default_renderer"} if stored.kind in LEGACY_RENDERERS else set()
            unexpected = set(fields).difference(current_fields, removable)
            if unexpected:
                raise RuntimeError(
                    f"Diagram {stored.pk!s} has unsupported Mermaiden 13.1.0 configuration fields: "
                    f"{', '.join(sorted(unexpected))}."
                )
            migrated_fields = {
                **current_fields,
                **{name: value for name, value in fields.items() if name in current_fields},
            }
            if stored.kind in LEGACY_RENDERERS:
                renderer = fields.get("default_renderer")
                if renderer is None:
                    renderer = None
                elif not isinstance(renderer, Mapping) or set(renderer) != {"$enum", "value"}:
                    raise RuntimeError(f"Diagram {stored.pk!s} legacy renderer must be a typed enum value.")
                if renderer is not None and renderer.get("$enum") != LEGACY_RENDERERS[stored.kind]:
                    raise RuntimeError(f"Diagram {stored.pk!s} legacy renderer type is not supported.")
                if renderer is not None:
                    renderer_value = renderer.get("value")
                    if not isinstance(renderer_value, str) or renderer_value not in LAYOUTS:
                        raise RuntimeError(f"Diagram {stored.pk!s} legacy renderer value is not supported.")
                    layout = current_fields["layout"]
                    if not isinstance(layout, Mapping):
                        raise RuntimeError(f"Diagram {stored.pk!s} current layout must be a typed value.")
                    migrated_fields["layout"] = {
                        **layout,
                        "fields": {"root": LAYOUTS[renderer_value]},
                    }

            candidate = {
                **snapshot,
                "version": 9,
                "configuration": {
                    **configuration,
                    "fields": migrated_fields,
                },
            }
            diagram = application.restore(candidate)
            canonical = application.snapshot(diagram).to_dict()
            if canonical["kind"] != stored.kind:
                raise RuntimeError(
                    f"Diagram {stored.pk!s} kind mismatch: record has {stored.kind!r}, "
                    f"snapshot has {canonical['kind']!r}."
                )
            if canonical["draft"] is True:
                source = ""
            else:
                report = application.validate_render(diagram)
                if not report.success:
                    diagnostics = "; ".join(
                        f"{diagnostic.code.value}: {diagnostic.message} {diagnostic.details}".strip()
                        for diagnostic in report.diagnostics
                    )
                    raise RuntimeError(
                        f"Diagram {stored.pk!s} failed Mermaiden render validation: "
                        f"{diagnostics or 'no diagnostic was returned.'}"
                    )
                source = application.render(diagram)
            diagram_model.objects.using(database).filter(pk=stored.pk).update(
                snapshot=canonical,
                source=source,
            )
    finally:
        application.close()


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("diagrams", "0005_upgrade_mermaiden_11_0_1_snapshots"),
    ]

    operations = [
        migrations.RunPython(upgrade_snapshots),
    ]
