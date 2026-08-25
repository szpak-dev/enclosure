from pathlib import Path

import pytest
from django.test import Client

SIREN_MEDIA_TYPE = "application/vnd.siren+json"


@pytest.fixture
def client() -> Client:
    return Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE)


@pytest.fixture
def registered_project(tmp_path: Path) -> tuple[str, Path]:
    setup = Client()
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "app.py").write_text("", encoding="utf-8")
    category = setup.post(
        "/api/records/categories",
        data={"title": "Project", "content_schema": {"type": "object"}},
        content_type="application/json",
    ).json()
    tag = setup.post(
        "/api/records/tags",
        data={"name": "project"},
        content_type="application/json",
    ).json()
    record = setup.post(
        "/api/records",
        data={
            "title": "Project",
            "content": {},
            "category_id": category["id"],
            "tag_ids": [tag["id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    scaffolding = setup.post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Package",
            "description": "Creates a package.",
            "spec": {
                "language": "python",
                "variables": [],
                "templates": [
                    {
                        "path": "__init__.py",
                        "content": "generated\n",
                        "write_mode": "create_if_missing",
                    }
                ],
            },
        },
        content_type="application/json",
    ).json()
    discovery = setup.post(
        "/api/projects/discoveries",
        data={"root": str(tmp_path)},
        content_type="application/json",
    ).json()
    project = setup.post(
        "/api/projects",
        data={
            "discovery": discovery,
            "architecture_root": str(tmp_path),
            "boundaries_yaml": "boundaries: {}\n",
            "shape_yaml": "shape:\n  realms:\n    - name: project\n      match: '*'\n",
            "scaffolding_id": scaffolding["id"],
            "record_ids": [record["id"]],
        },
        content_type="application/json",
    ).json()
    return project["id"], tmp_path


@pytest.mark.django_db
def test_siren_generates_project_source(
    client: Client,
    registered_project: tuple[str, Path],
) -> None:
    project_id, root = registered_project
    details = client.get(f"/siren/projects/{project_id}")

    assert details.status_code == 200
    assert {
        (link["title"], link["href"])
        for link in details.json()["links"]
    } >= {
        (
            "Architecture configuration",
            f"http://testserver/siren/projects/{project_id}/architecture-configuration",
        )
    }
    action = next(action for action in details.json()["actions"] if action["name"] == "generate_project_source")
    assert action["href"] == f"http://testserver/siren/projects/{project_id}/source-generations"
    assert action["method"] == "POST"
    assert [field["name"] for field in action["fields"]] == ["destination"]
    structured_form = action["https://modwire.dev/siren/structured-form/v1"]
    assert [control["name"] for control in structured_form["controls"]] == ["parameters"]

    generated = client.post(
        action["href"].removeprefix("http://testserver"),
        data={"destination": "generated", "parameters": {}},
        content_type="application/json",
    )

    assert generated.status_code == 200
    assert generated["Content-Type"] == SIREN_MEDIA_TYPE
    assert generated.json()["class"] == ["command-result"]
    assert generated.json()["properties"] == {"files": ["generated/__init__.py"]}
    assert (root / "generated" / "__init__.py").read_text(encoding="utf-8") == "generated\n"
