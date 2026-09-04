from pathlib import Path
from urllib.parse import urlsplit

import pytest
from django.test import Client

SIREN_MEDIA_TYPE = "application/vnd.siren+json"


@pytest.fixture
def client() -> Client:
    return Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE)


@pytest.fixture
def registered_project(tmp_path: Path) -> tuple[str, str, Path, str]:
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
    resolution = setup.post(
        "/api/projects",
        data={
            "discovery": discovery,
            "architecture_root": str(tmp_path),
            "boundaries_yaml": "boundaries: {}\n",
            "shape_yaml": "shape:\n  realms:\n    - name: project\n      match: '*'\n",
            "scaffolding_id": scaffolding["id"],
            "record_ids": [],
        },
        content_type="application/json",
    ).json()
    return resolution["project"]["id"], resolution["workspace"]["id"], tmp_path, record["id"]


@pytest.mark.django_db
def test_siren_generates_project_source(
    client: Client,
    registered_project: tuple[str, str, Path, str],
) -> None:
    project_id, workspace_id, root, _ = registered_project
    details = client.get(f"/siren/projects/{project_id}")
    workspace_details = client.get(f"/siren/projects/{project_id}/workspaces/{workspace_id}")

    assert details.status_code == 200
    configurations_link = next(
        link
        for link in details.json()["links"]
        if link["href"] == f"http://testserver/siren/projects/{project_id}/architecture-configurations"
    )
    assert configurations_link["rel"] == ["collection"]
    configurations = client.get(configurations_link["href"].removeprefix("http://testserver"))
    assert configurations.status_code == 200
    configuration_link = configurations.json()["entities"][0]["links"][0]
    configuration = client.get(configuration_link["href"].removeprefix("http://testserver"))
    assert configuration.status_code == 200
    assert configuration.json()["properties"] == {
        "id": configuration_link["href"].split("/")[-1],
        "project_id": project_id,
        "boundaries_yaml": "boundaries: {}\n",
        "shape_yaml": "shape:\n  realms:\n    - name: project\n      match: '*'\n",
    }
    action = next(
        action for action in workspace_details.json()["actions"] if action["name"] == "generate_project_source"
    )
    assert action["href"] == (
        f"http://testserver/siren/projects/{project_id}/workspaces/{workspace_id}/source-generations"
    )
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


@pytest.mark.django_db
def test_siren_exposes_operating_contract_lifecycle(
    client: Client,
    registered_project: tuple[str, str, Path, str],
) -> None:
    project_id, _, project_root, record_id = registered_project
    root = client.get("/siren/").json()
    create_action = next(action for action in root["actions"] if action["name"] == "create_operating_contract")
    context_action = next(action for action in root["actions"] if action["name"] == "get_workspace_context")
    assert create_action["method"] == "POST"
    assert [field["name"] for field in create_action["fields"]] == ["title", "authority", "provenance"]
    assert context_action["method"] == "POST"
    assert [field["name"] for field in context_action["fields"]] == ["root", "task"]

    created = client.post(
        urlsplit(create_action["href"]).path,
        data={
            "title": "Example Siren operating contract",
            "authority": "example:siren:operating-contract",
            "provenance": "example-siren-test",
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    contract = created.json()["properties"]
    created_actions = {action["name"]: action for action in created.json()["actions"]}
    assert "get_operating_contract" in created_actions

    published = client.post(
        f"/siren/projects/operating-contracts/{contract['id']}/revisions",
        data={"record_ids": [record_id], "references": []},
        content_type="application/json",
    )
    assert published.status_code == 201
    assert published.json()["properties"]["contract_id"] == contract["id"]
    assert published.json()["properties"]["version"] == 1

    retrieved = client.get(urlsplit(created_actions["get_operating_contract"]["href"]).path)
    assert retrieved.status_code == 200
    assert retrieved.json()["properties"] == contract

    project = client.get(f"/siren/projects/{project_id}").json()
    project_actions = {action["name"]: action for action in project["actions"]}
    assert {
        "bind_project_operating_contract",
        "get_project_operating_contract_binding",
        "replace_project_operating_contract_binding",
    } <= project_actions.keys()

    unconfigured = client.get(urlsplit(project_actions["get_project_operating_contract_binding"]["href"]).path)
    assert unconfigured.status_code == 409

    binding = {
        "contract_id": contract["id"],
        "version": 1,
        "update_policy": "pinned",
    }
    bound = client.post(
        urlsplit(project_actions["bind_project_operating_contract"]["href"]).path,
        data=binding,
        content_type="application/json",
    )
    assert bound.status_code == 201
    assert bound.json()["properties"]["state"] == "configured"
    assert bound.json()["properties"]["effective_revision"]["version"] == 1

    replaced = client.put(
        urlsplit(project_actions["replace_project_operating_contract_binding"]["href"]).path,
        data={**binding, "update_policy": "follow-latest"},
        content_type="application/json",
    )
    assert replaced.status_code == 200
    assert replaced.json()["properties"]["update_policy"] == "follow-latest"

    fetched = client.get(urlsplit(project_actions["get_project_operating_contract_binding"]["href"]).path)
    assert fetched.status_code == 200
    assert fetched.json()["properties"] == replaced.json()["properties"]

    context = client.post(
        urlsplit(context_action["href"]).path,
        data={"root": str(project_root), "task": "Apply project guidance"},
        content_type="application/json",
    )
    assert context.status_code == 200
    assert context["Content-Type"] == SIREN_MEDIA_TYPE
    assert context.json()["properties"]["receipt"]["items"][0]["record_id"] == record_id
    assert context.json()["properties"]["receipt"]["stop_condition"] == "selected-guidance-and-checks"


@pytest.mark.django_db
def test_siren_exposes_guidance_relationship_identity(
    client: Client,
    registered_project: tuple[str, str, Path, str],
) -> None:
    project_id, _, _, record_id = registered_project
    project = client.get(f"/siren/projects/{project_id}").json()
    relationships_link = next(
        link
        for link in project["links"]
        if link["href"] == f"http://testserver/siren/projects/{project_id}/guidance-relationships"
    )
    relationships = client.get(urlsplit(relationships_link["href"]).path)
    actions = {action["name"]: action for action in relationships.json()["actions"]}
    replace_action = actions["replace_guidance_relationships"]

    assert relationships_link["rel"] == ["collection"]
    assert relationships.status_code == 200
    assert replace_action["method"] == "PUT"
    assert [
        control["name"] for control in replace_action["https://modwire.dev/siren/structured-form/v1"]["controls"]
    ] == ["relationships"]

    replaced = client.put(
        urlsplit(replace_action["href"]).path,
        data={
            "relationships": [
                {
                    "source_record_id": record_id,
                    "target_record_id": record_id,
                    "kind": "containment",
                }
            ]
        },
        content_type="application/json",
    )
    found = client.get(urlsplit(relationships_link["href"]).path)

    assert replaced.status_code == 200
    assert found.status_code == 200
    properties = found.json()["entities"][0]["properties"]
    assert properties == {
        "id": properties["id"],
        "project_id": project_id,
        "source_record_id": record_id,
        "target_record_id": record_id,
        "kind": "containment",
    }
