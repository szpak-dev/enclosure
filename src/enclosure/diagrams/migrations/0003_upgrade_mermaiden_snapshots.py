import re
from collections.abc import Mapping

from django.db import migrations
from mermaiden import Application


def _snake_case(name: str) -> str:
    words = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", words).lower()


def _discriminator(owner: str, category: str, reference: object) -> str:
    if not isinstance(reference, str):
        raise RuntimeError("Mermaiden snapshot discriminator must be a string.")
    _, separator, qualified_name = reference.partition(":")
    if not separator:
        raise RuntimeError(f"Unsupported Mermaiden version 4 discriminator {reference!r}.")
    class_name = qualified_name.rsplit(".", 1)[-1]
    return f"mermaiden/{category}/{owner}/{_snake_case(class_name)}"


def _value(
    value: object,
    owner: str,
    categories: Mapping[str, str],
    typed_category: str = "value",
) -> object:
    if isinstance(value, list):
        return [_value(item, owner, categories, typed_category) for item in value]
    if not isinstance(value, Mapping):
        return value
    if "$enum" in value:
        return {
            "$enum": _discriminator(owner, "enum", value["$enum"]),
            "value": value["value"],
        }
    if "$type" in value:
        reference = value["$type"]
        return {
            "$type": _discriminator(owner, categories.get(reference, typed_category), reference),
            "fields": _value(value["fields"], owner, categories),
        }
    return {
        key: _value(item, owner, categories, "element" if key == "elements" else "value") for key, item in value.items()
    }


def _typed(
    value: object,
    owner: str,
    category: str,
    categories: Mapping[str, str],
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"Mermaiden snapshot {category} must be an object.")
    return {
        "$type": _discriminator(owner, category, value["$type"]),
        "fields": _value(value["fields"], owner, categories),
    }


def _upgrade(snapshot: object) -> dict[str, object]:
    if not isinstance(snapshot, Mapping):
        raise RuntimeError("Mermaiden snapshot must be an object.")
    version = snapshot.get("version")
    if version == 6:
        return dict(snapshot)
    if version != 4:
        raise RuntimeError(f"Unsupported Mermaiden snapshot version {version!r}; expected 4 or 6.")
    owner = snapshot.get("kind")
    if not isinstance(owner, str) or not owner:
        raise RuntimeError("Mermaiden snapshot kind must be a non-empty string.")
    root_collections = {
        "elements": "element",
        "relations": "relation",
        "annotations": "annotation",
    }
    categories = {snapshot["configuration"]["$type"]: "configuration"}
    categories.update(
        (item["$type"], category) for collection, category in root_collections.items() for item in snapshot[collection]
    )
    return {
        "version": 6,
        "kind": owner,
        "draft": snapshot["draft"],
        "configuration": _typed(snapshot["configuration"], owner, "configuration", categories),
        "elements": [_typed(item, owner, "element", categories) for item in snapshot["elements"]],
        "relations": [_typed(item, owner, "relation", categories) for item in snapshot["relations"]],
        "annotations": [_typed(item, owner, "annotation", categories) for item in snapshot["annotations"]],
        "properties": _value(snapshot["properties"], owner, categories),
    }


def upgrade_snapshots(apps, schema_editor) -> None:
    diagram_model = apps.get_model("diagrams", "Diagram")
    database = schema_editor.connection.alias
    application = Application.create()
    try:
        for stored in diagram_model.objects.using(database).all().iterator():
            upgraded = _upgrade(stored.snapshot)
            diagram = application.restore(upgraded)
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
        ("diagrams", "0002_remove_diagram_interactions"),
    ]

    operations = [
        migrations.RunPython(upgrade_snapshots),
    ]
