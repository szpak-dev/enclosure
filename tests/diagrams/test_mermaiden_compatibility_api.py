import json
import re
from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone
from mermaiden import Application, SnapshotUpgradeError

pytestmark = pytest.mark.django_db


def test_browser_mermaid_runtime_matches_mermaiden_compatibility_version() -> None:
    package = json.loads((Path(__file__).parents[2] / "browser" / "package.json").read_text())
    renderer_package = json.loads((Path(__file__).parents[2] / "package.json").read_text())

    with Application.create() as application:
        mermaiden_version = application.mermaid_version
        mermaiden_cli_version = application.mermaid_cli_version

    assert package["dependencies"]["mermaid"] == mermaiden_version
    assert renderer_package["devDependencies"] == {
        "@mermaid-js/mermaid-cli": mermaiden_cli_version,
        "mermaid": mermaiden_version,
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("fixture_name", "invalid_renderer", "diagram_index"),
    (
        ("mermaiden-11.0.1-flowchart-v8.json", False, None),
        ("mermaiden-11.0.0-sequence.json", False, None),
        ("mermaiden-11.0.1-flowchart-v8.json", True, None),
        ("mermaiden-13.1.0-architecture.json", False, 0),
        ("mermaiden-13.1.0-architecture.json", False, 1),
        ("mermaiden-13.1.0-architecture.json", False, 2),
        ("mermaiden-13.1.0-architecture.json", False, 3),
        ("mermaiden-13.1.0-er-attribute.json", False, None),
    ),
)
def test_saved_diagrams_upgrade_through_public_migration_commands(
    client: Client,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fixture_name: str,
    invalid_renderer: bool,
    diagram_index: int | None,
) -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures" / fixture_name).read_text())
    if diagram_index is not None:
        fixture = fixture["diagrams"][diagram_index]
    snapshot = fixture["snapshot"]
    if invalid_renderer:
        snapshot["configuration"]["fields"]["default_renderer"] = None
    timestamp = timezone.now().isoformat()
    saved = tmp_path / "example-saved-diagram.json"
    saved.write_text(
        json.dumps(
            [
                {
                    "model": "diagrams.diagramset",
                    "pk": "example-set",
                    "fields": {
                        "title": "Example saved diagrams",
                        "description": "Example migration input",
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                },
                {
                    "model": "diagrams.diagram",
                    "pk": "example-diagram",
                    "fields": {
                        "diagram_set": "example-set",
                        "title": "Example saved diagram",
                        "kind": snapshot["kind"],
                        "snapshot": snapshot,
                        "source": fixture["source"],
                        "revision": 1,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                },
            ]
        )
    )
    monkeypatch.setenv("DIAGRAM_SNAPSHOT_BACKUP_DIRECTORY", str(tmp_path))
    try:
        previous = "0006" if snapshot["version"] == 9 else "0005"
        call_command("migrate", "diagrams", previous, fake=True, verbosity=0)
        call_command("loaddata", str(saved), verbosity=0)

        if invalid_renderer:
            before = client.get("/api/diagrams/example-diagram").json()
            with pytest.raises(SnapshotUpgradeError):
                call_command("migrate", "diagrams", verbosity=0)
            assert client.get("/api/diagrams/example-diagram").json() == before
            backup = next(tmp_path.glob("0008-mermaiden-15-*.json"))
            assert json.loads(backup.read_text())[0]["fields"]["snapshot"] == snapshot
            return

        call_command("migrate", "diagrams", verbosity=0)

        response = client.get("/api/diagrams/example-diagram")
        assert response.status_code == 200
        stored = response.json()
        with Application.create() as application:
            identity = application.snapshot_contract_identity(snapshot["kind"])
        assert stored["snapshot"]["version"] == identity.snapshot_version
        assert stored["revision"] == 2
        backups = tuple(tmp_path.glob("0008-mermaiden-15-*.json"))
        assert len(backups) == 1
        backed_up = json.loads(backups[0].read_text())[0]["fields"]
        assert backed_up["snapshot"] == snapshot
        assert backed_up["revision"] == 1
        assert backed_up["snapshot"]["annotations"] == snapshot["annotations"]
        assert stored["snapshot"]["elements"] == snapshot["elements"]
        assert stored["snapshot"]["annotations"] == (
            [] if snapshot["kind"] in {"classDiagram", "treeView-beta"} else snapshot["annotations"]
        )
        if snapshot["kind"] == "classDiagram":
            assert "html_labels" not in stored["snapshot"]["configuration"]["fields"]
            assert {
                **stored["snapshot"]["configuration"]["fields"],
                "html_labels": snapshot["configuration"]["fields"]["html_labels"],
            } == snapshot["configuration"]["fields"]
        elif diagram_index is not None:
            assert stored["snapshot"]["configuration"] == snapshot["configuration"]
        if snapshot["kind"] == "flowchart":
            fields = stored["snapshot"]["configuration"]["fields"]
            assert stored["snapshot"]["draft"] is True
            assert stored["source"] == ""
            assert "default_renderer" not in fields
            layout = fields["layout"]["fields"]["root"]
            assert layout == "dagre"
            assert fields["wrapping_width"] == 200.0
            assert fields["min_node_width"] == 120.0
        elif snapshot["kind"] == "sequenceDiagram":
            assert stored["snapshot"]["kind"] == "sequenceDiagram"
            assert "sequenceDiagram" in stored["source"]
            assert "Prepare plan" in stored["source"]
    finally:
        call_command("migrate", "diagrams", fake=True, verbosity=0)


def create_diagram(client: Client, kind: str, title: str) -> dict[str, object]:
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": title, "description": f"Compatibility proof for {title}."},
        content_type="application/json",
    )
    assert diagram_set.status_code == 201
    response = client.post(
        f"/api/diagram-sets/{diagram_set.json()['id']}/diagrams",
        data={"title": title, "kind": kind},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


def apply_batch(client: Client, diagram: dict[str, object], commands: list[dict[str, object]]) -> None:
    response = client.post(
        f"/api/diagrams/{diagram['id']}/command-batches",
        data={"expected_revision": diagram["revision"], "commands": commands},
        content_type="application/json",
    )
    assert response.status_code == 200
    diagram["revision"] = response.json()["revision"]


def apply_command(
    client: Client, diagram: dict[str, object], operation: str, arguments: dict[str, object]
) -> dict[str, object]:
    response = client.post(
        f"/api/diagrams/{diagram['id']}/commands",
        data={
            "expected_revision": diagram["revision"],
            "operation": operation,
            "arguments": arguments,
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    return response.json()


def sequence_commands(label: str) -> list[dict[str, object]]:
    return [
        {
            "operation": "add_participant",
            "arguments": {"id": "example-requester", "label": "Example requester"},
        },
        {
            "operation": "add_participant",
            "arguments": {"id": "example-worker", "label": "Example worker"},
        },
        {
            "operation": "add_message",
            "arguments": {
                "id": "example-request",
                "source_id": "example-requester",
                "target_id": "example-worker",
                "label": label,
            },
        },
    ]


def test_render_rejection_during_creation_leaves_the_diagram_set_empty() -> None:
    client = Client()
    diagram_set = client.post(
        "/api/diagram-sets",
        data={"title": "Example rejected creation", "description": "Example render validation attack."},
        content_type="application/json",
    ).json()

    rejected = client.post(
        f"/api/diagram-sets/{diagram_set['id']}/diagram-batches",
        data={
            "title": "Example oversized sequence",
            "kind": "sequenceDiagram",
            "commands": sequence_commands("Example oversized message " + "x" * 50_000),
        },
        content_type="application/json",
    )

    assert rejected.status_code == 422
    assert rejected.json()["detail"].startswith("Mermaiden render validation failed [render_failed]:")
    assert "Maximum text size in diagram exceeded" in rejected.json()["detail"]
    diagrams = client.get(f"/api/diagram-sets/{diagram_set['id']}/diagrams")
    assert diagrams.status_code == 200
    assert diagrams.json()["items"] == []


def test_render_rejection_during_update_preserves_content_and_allows_recovery() -> None:
    client = Client()
    diagram = create_diagram(client, "sequenceDiagram", "Example rejected update")
    apply_batch(client, diagram, sequence_commands("Example accepted message")[:2])
    before = client.get(f"/api/diagrams/{diagram['id']}").json()

    rejected = client.post(
        f"/api/diagrams/{diagram['id']}/commands",
        data={
            "expected_revision": before["revision"],
            **sequence_commands("Example oversized message " + "x" * 50_000)[2],
        },
        content_type="application/json",
    )

    assert rejected.status_code == 422
    assert rejected.json()["detail"].startswith("Mermaiden render validation failed [render_failed]:")
    assert client.get(f"/api/diagrams/{diagram['id']}").json() == before

    recovered = apply_command(
        client,
        before,
        "add_message",
        {
            "id": "example-request",
            "source_id": "example-requester",
            "target_id": "example-worker",
            "label": "Example accepted message",
        },
    )
    assert recovered["revision"] == before["revision"] + 1
    assert "Example accepted message" in recovered["source"]


def test_render_rejection_during_update_batch_preserves_snapshot_source_and_revision() -> None:
    client = Client()
    diagram = create_diagram(client, "sequenceDiagram", "Example rejected update batch")
    apply_batch(client, diagram, sequence_commands("Example accepted message")[:2])
    before = client.get(f"/api/diagrams/{diagram['id']}").json()

    rejected = client.post(
        f"/api/diagrams/{diagram['id']}/command-batches",
        data={
            "expected_revision": before["revision"],
            "commands": [sequence_commands("Example oversized message " + "x" * 50_000)[2]],
        },
        content_type="application/json",
    )

    assert rejected.status_code == 422
    assert rejected.json()["detail"].startswith("Mermaiden render validation failed [render_failed]:")
    stored = client.get(f"/api/diagrams/{diagram['id']}").json()
    assert stored["snapshot"] == before["snapshot"]
    assert stored["source"] == before["source"]
    assert stored["revision"] == before["revision"]


def test_sequence_text_with_semicolon_survives_restore_and_render() -> None:
    client = Client()
    diagram = create_diagram(client, "sequenceDiagram", "Sequence compatibility")
    apply_batch(
        client,
        diagram,
        [
            {
                "operation": "add_participant",
                "arguments": {"id": "requester", "label": "Requester"},
            },
            {
                "operation": "add_participant",
                "arguments": {"id": "worker", "label": "Worker"},
            },
        ],
    )

    stored = apply_command(
        client,
        diagram,
        "add_message",
        {
            "id": "decision",
            "source_id": "requester",
            "target_id": "worker",
            "label": "Decide; then continue",
        },
    )

    assert "Decide#59; then continue" in stored["source"]
    assert "Decide; then continue" in json.dumps(stored["snapshot"])


def test_state_text_with_semicolon_survives_restore_and_render() -> None:
    client = Client()
    diagram = create_diagram(client, "stateDiagram-v2", "State compatibility")
    apply_batch(
        client,
        diagram,
        [
            {
                "operation": "add_state",
                "arguments": {"id": "ready", "label": "Ready"},
            }
        ],
    )

    stored = apply_command(
        client,
        diagram,
        "add_note",
        {
            "id": "guidance",
            "state_id": "ready",
            "text": "Wait; then continue",
        },
    )

    assert '"Wait; then continue"' in stored["source"]
    assert "Wait; then continue" in json.dumps(stored["snapshot"])


def test_entity_path_identifiers_survive_restore_and_render() -> None:
    client = Client()
    diagram = create_diagram(client, "erDiagram", "Entity compatibility")
    source_id = "src/example/domain/models.py"
    target_id = "src/example/application/service.py"
    apply_batch(
        client,
        diagram,
        [
            {
                "operation": "add_entity",
                "arguments": {"id": source_id, "label": "Example source"},
            },
            {
                "operation": "add_entity",
                "arguments": {"id": target_id, "label": "Example target"},
            },
        ],
    )

    stored = apply_command(
        client,
        diagram,
        "add_relationship",
        {
            "id": "dependency",
            "source_id": source_id,
            "target_id": target_id,
            "label": "uses",
        },
    )

    assert source_id not in stored["source"]
    assert target_id not in stored["source"]
    assert len(re.findall(r"e_h_[0-9a-f]{32}", stored["source"])) >= 4
    snapshot = json.dumps(stored["snapshot"])
    assert source_id in snapshot
    assert target_id in snapshot
