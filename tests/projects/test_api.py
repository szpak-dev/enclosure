from pathlib import Path

import pytest
from django.test import Client
from django.test.utils import override_settings

BOUNDARIES_YAML = """boundaries:
  tags:
    - name: module
      match: "*"
  flow:
    module_tag: module
    layers: []
    analyzers: []
"""
HEALTHY_SHAPE_YAML = """shape:
  realms:
    - name: project
      match: "*"
      shape:
        max_classes_per_file: 1
"""
UNHEALTHY_SHAPE_YAML = """shape:
  realms:
    - name: project
      match: "*"
      shape:
        max_classes_per_file: 0
"""


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def dependencies(client: Client) -> dict[str, str]:
    category = client.post(
        "/api/records/categories",
        data={"title": "Project context", "content_schema": {"type": "object"}},
        content_type="application/json",
    )
    assert category.status_code == 201

    tag = client.post(
        "/api/records/tags",
        data={"name": "project"},
        content_type="application/json",
    )
    assert tag.status_code == 201

    record = client.post(
        "/api/records",
        data={
            "title": "Project context",
            "content": {},
            "category_id": category.json()["id"],
            "tag_ids": [tag.json()["id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    assert record.status_code == 201

    scaffolding = client.post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Project package",
            "description": "Creates a project package.",
            "spec": {
                "language": "python",
                "variables": [],
                "templates": [
                    {
                        "path": "src/package/__init__.py",
                        "content": "",
                        "write_mode": "overwrite",
                    },
                ],
            },
        },
        content_type="application/json",
    )
    assert scaffolding.status_code == 201

    return {
        "category_id": category.json()["id"],
        "record_id": record.json()["id"],
        "scaffolding_id": scaffolding.json()["id"],
        "tag_id": tag.json()["id"],
    }


def discover(client: Client, root: Path) -> dict:
    response = client.post(
        "/api/projects/discoveries",
        data={"root": str(root)},
        content_type="application/json",
    )
    assert response.status_code == 200
    return response.json()


def registration(
    discovery: dict,
    dependencies: dict[str, str],
    shape_yaml: str = HEALTHY_SHAPE_YAML,
) -> dict:
    return {
        "discovery": discovery,
        "architecture_root": discovery["root"],
        "boundaries_yaml": BOUNDARIES_YAML,
        "shape_yaml": shape_yaml,
        "scaffolding_id": dependencies["scaffolding_id"],
        "record_ids": [dependencies["record_id"]],
    }


def python_project(root: Path) -> None:
    (root / "uv.lock").write_text("", encoding="utf-8")
    (root / "app.py").write_text("class Application:\n    pass\n", encoding="utf-8")


@pytest.mark.django_db
def test_discovers_python_project_without_changing_its_root(client: Client, tmp_path: Path) -> None:
    python_project(tmp_path)

    response = client.post(
        "/api/projects/discoveries",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "root": str(tmp_path),
        "stack": {
            "language": "python",
            "language_version": "",
            "package_manager": "uv",
        },
    }


@pytest.mark.django_db
def test_discovery_rejects_missing_directory(client: Client, tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    response = client.post(
        "/api/projects/discoveries",
        data={"root": str(missing)},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": f"Invalid project root: {missing}"}


@pytest.mark.django_db
def test_discovery_rejects_project_without_package_manager(client: Client, tmp_path: Path) -> None:
    response = client.post(
        "/api/projects/discoveries",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Package manager could not be recognized."}


@pytest.mark.django_db
def test_discovery_rejects_ambiguous_package_managers(client: Client, tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    response = client.post(
        "/api/projects/discoveries",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith("Ambiguous package manager: ")
    assert "python/uv" in response.json()["detail"]
    assert "typescript/npm" in response.json()["detail"]


@pytest.mark.django_db
def test_registers_discovered_project(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 201
    assert response.json() == {
        "project": {
            "id": response.json()["project"]["id"],
            "title": tmp_path.name,
            "language_id": "python",
            "language_version": "",
            "package_manager_id": "uv",
            "scaffolding_id": dependencies["scaffolding_id"],
        },
        "workspace": {
            "id": response.json()["workspace"]["id"],
            "project_id": response.json()["project"]["id"],
            "root": str(tmp_path),
            "architecture_root": str(tmp_path),
            "revision": 1,
        },
    }


@pytest.mark.django_db
def test_publishes_and_binds_versioned_operating_contract(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    contract_response = client.post(
        "/api/projects/operating-contracts",
        data={
            "title": "Example Python delivery contract",
            "authority": "example:engineering:python-delivery",
            "provenance": "example-repository",
        },
        content_type="application/json",
    )
    assert contract_response.status_code == 201
    contract = contract_response.json()

    first_response = client.post(
        f"/api/projects/operating-contracts/{contract['id']}/revisions",
        data={
            "record_ids": [dependencies["record_id"]],
            "references": [
                {
                    "kind": "policy",
                    "id": "example-python-policy",
                    "authority": "example:policy:python",
                    "revision": "3",
                }
            ],
        },
        content_type="application/json",
    )
    assert first_response.status_code == 201
    first = first_response.json()
    assert first["version"] == 1
    assert [reference["kind"] for reference in first["references"]] == ["guidance", "policy"]

    second_response = client.post(
        f"/api/projects/operating-contracts/{contract['id']}/revisions",
        data={
            "record_ids": [dependencies["record_id"]],
            "references": [
                {
                    "kind": "architecture",
                    "id": "example-python-architecture",
                    "authority": "example:architecture:python",
                    "revision": "5",
                }
            ],
        },
        content_type="application/json",
    )
    assert second_response.status_code == 201
    assert second_response.json()["version"] == 2
    assert client.get(f"/api/projects/operating-contracts/{contract['id']}/revisions/1").json() == first

    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] = []
    project_response = client.post("/api/projects", data=payload, content_type="application/json")
    assert project_response.status_code == 201
    project = project_response.json()["project"]

    unconfigured = client.get(f"/api/projects/{project['id']}/operating-contract-binding")
    assert unconfigured.status_code == 409
    assert unconfigured.json() == {"state": "unconfigured", "project_id": project["id"]}
    context = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )
    assert context.status_code == 200
    assert context.json()["readiness"] == "incomplete"
    assert context.json()["receipt"]["diagnostics"][0]["code"] == "mandatory_contract_unconfigured"

    binding_data = {
        "contract_id": contract["id"],
        "version": 1,
        "update_policy": "pinned",
    }
    bound = client.post(
        f"/api/projects/{project['id']}/operating-contract-bindings",
        data=binding_data,
        content_type="application/json",
    )
    assert bound.status_code == 201
    assert bound.json()["effective_revision"]["version"] == 1
    duplicate = client.post(
        f"/api/projects/{project['id']}/operating-contract-bindings",
        data={**binding_data, "version": 2},
        content_type="application/json",
    )
    assert duplicate.status_code == 422

    replaced = client.put(
        f"/api/projects/{project['id']}/operating-contract-binding",
        data={**binding_data, "update_policy": "follow-latest"},
        content_type="application/json",
    )
    assert replaced.status_code == 200
    assert replaced.json()["bound_revision"] == 1
    assert replaced.json()["effective_revision"]["version"] == 2


@pytest.mark.django_db
def test_registration_rejects_invalid_architecture_yaml(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies, shape_yaml="shape: [")

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json()["detail"].startswith("Invalid architecture configuration:")


@pytest.mark.django_db
def test_lists_and_fetches_registered_projects(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    created = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    )
    assert created.status_code == 201
    resolution = created.json()
    project = resolution["project"]

    listed = client.get("/api/projects")
    found = client.post(
        "/api/projects/root-search-results",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )
    resolved = client.post(
        "/api/projects/workspace-resolutions",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )
    fetched = client.get(f"/api/projects/{project['id']}")

    assert listed.status_code == 200
    assert listed.json() == [{"id": project["id"], "title": project["title"]}]
    assert found.status_code == 200
    assert found.json() == project
    assert resolved.status_code == 200
    assert resolved.json() == resolution
    assert fetched.status_code == 200
    assert fetched.json() == project


@pytest.mark.django_db
def test_binds_multiple_worktrees_and_uses_the_selected_workspace(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    main = tmp_path / "main"
    feature = tmp_path / "feature"
    main.mkdir()
    feature.mkdir()
    python_project(main)
    python_project(feature)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, main), dependencies),
        content_type="application/json",
    ).json()
    project = resolution["project"]

    bound = client.post(
        f"/api/projects/{project['id']}/workspaces",
        data={"root": str(feature), "architecture_root": str(feature)},
        content_type="application/json",
    )
    resolved = client.post(
        "/api/projects/workspace-resolutions",
        data={"root": str(feature)},
        content_type="application/json",
    )
    generated = client.post(
        f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}/source-generations",
        data={"destination": "generated", "parameters": {}},
        content_type="application/json",
    )
    workspaces = client.get(f"/api/projects/{project['id']}/workspaces")
    fetched = client.get(f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}")
    deleted = client.delete(
        f"/api/projects/{project['id']}/workspaces/{bound.json()['id']}",
        data={"expected_revision": 1},
        content_type="application/json",
    )

    assert bound.status_code == 201
    assert bound.json() == {
        "id": bound.json()["id"],
        "project_id": project["id"],
        "root": str(feature),
        "architecture_root": str(feature),
        "revision": 1,
    }
    assert resolved.status_code == 200
    assert resolved.json() == {"project": project, "workspace": bound.json()}
    assert workspaces.json() == [
        bound.json(),
        resolution["workspace"],
    ]
    assert fetched.json() == bound.json()
    assert generated.status_code == 200
    assert (feature / "generated" / "src" / "package" / "__init__.py").is_file()
    assert not (main / "generated").exists()
    assert deleted.status_code == 204
    assert client.get(f"/api/projects/{project['id']}/workspaces").json() == [resolution["workspace"]]


@pytest.mark.django_db
def test_rebinds_a_moved_workspace_without_changing_project_identity_or_title(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    original = tmp_path / "original-checkout"
    relocated = tmp_path / "relocated-checkout"
    original.mkdir()
    python_project(original)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, original), dependencies),
        content_type="application/json",
    ).json()
    project = resolution["project"]
    workspace = resolution["workspace"]
    original.rename(relocated)

    stale = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/status")
    replaced = client.put(
        f"/api/projects/{project['id']}/workspaces/{workspace['id']}",
        data={
            "root": str(relocated),
            "architecture_root": str(relocated),
            "expected_revision": 1,
        },
        content_type="application/json",
    )
    conflicted = client.put(
        f"/api/projects/{project['id']}/workspaces/{workspace['id']}",
        data={
            "root": str(original),
            "architecture_root": str(original),
            "expected_revision": 1,
        },
        content_type="application/json",
    )
    resolved = client.post(
        "/api/projects/workspace-resolutions",
        data={"root": str(relocated)},
        content_type="application/json",
    )
    context = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(relocated), "task": "Continue after moving the checkout"},
        content_type="application/json",
    )

    assert stale.status_code == 200
    assert stale.json()["state"] == "missing_root"
    assert replaced.status_code == 200
    assert replaced.json() == {
        **workspace,
        "root": str(relocated),
        "architecture_root": str(relocated),
        "revision": 2,
    }
    assert conflicted.status_code == 422
    assert conflicted.json() == {
        "detail": f"Workspace {workspace['id']!r} revision conflict: expected 1, current revision is 2."
    }
    assert resolved.json() == {"project": project, "workspace": replaced.json()}
    assert resolved.json()["project"]["title"] == "original-checkout"
    assert context.status_code == 200
    assert context.json()["project_id"] == project["id"]
    assert context.json()["guidance"][0]["id"] == dependencies["record_id"]


@pytest.mark.django_db
def test_rejects_a_workspace_root_already_bound_to_another_project(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    python_project(first_root)
    python_project(second_root)
    first = client.post(
        "/api/projects",
        data=registration(discover(client, first_root), dependencies),
        content_type="application/json",
    ).json()
    second = client.post(
        "/api/projects",
        data=registration(discover(client, second_root), dependencies),
        content_type="application/json",
    ).json()

    conflict = client.post(
        f"/api/projects/{second['project']['id']}/workspaces",
        data={"root": str(first_root), "architecture_root": str(first_root)},
        content_type="application/json",
    )

    assert first["project"]["id"] != second["project"]["id"]
    assert conflict.status_code == 422
    assert conflict.json() == {"detail": f"Workspace root is already bound: {first_root}"}


@pytest.mark.django_db
def test_gets_ready_workspace_context_from_linked_records(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    created = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()["project"]

    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )

    context = response.json()

    assert response.status_code == 200
    assert context == {
        "project_id": created["id"],
        "root": str(tmp_path),
        "readiness": "ready",
        "guidance": [
            {
                "id": dependencies["record_id"],
                "title": "Project context",
                "summary": "Project context",
                "authority": f"record:{dependencies['record_id']}",
                "revision": context["guidance"][0]["revision"],
                "schema_revision": 1,
                "current_schema_revision": 1,
                "applies_when": [],
                "guidance": [],
                "checks": [],
            }
        ],
        "receipt": {
            "authority": {
                "kind": "project-operating-contract",
                "id": f"project:{created['id']}:operating-contract",
                "revision": "1",
                "provenance": "project-registration",
            },
            "items": [
                {
                    "record_id": dependencies["record_id"],
                    "title": "Project context",
                    "requirement": "mandatory",
                    "reason": "operating-contract",
                    "explanation": "Required by the active project operating contract.",
                    "authority": f"record:{dependencies['record_id']}",
                    "revision": context["guidance"][0]["revision"],
                    "checks": [],
                }
            ],
            "required_checks": [],
            "budget": {
                "used_optional_characters": 0,
                "optional_character_limit": 4096,
            },
            "coverage": {
                "status": "complete",
                "selected_count": 1,
                "omitted_count": 0,
                "diagnostic_count": 0,
            },
            "omissions": [],
            "diagnostics": [],
            "stop_condition": "selected-guidance-and-checks",
        },
    }


@pytest.mark.django_db
def test_routes_scoped_guidance_for_representative_tasks(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    database = client.post(
        "/api/records",
        data={
            "title": "Database delivery",
            "content": {
                "summary": "Safely deliver database changes.",
                "applies_when": ["database migration"],
                "guidance": ["Prepare a rollback before applying a migration."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [
                {
                    "path": "database.md",
                    "language": "markdown",
                    "content": "database migration rollback " * 20,
                }
            ],
        },
        content_type="application/json",
    )
    python = client.post(
        "/api/records",
        data={
            "title": "Python typing",
            "content": {
                "summary": "Keep Python typing strict.",
                "applies_when": ["python typing"],
                "guidance": ["Keep public annotations precise."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [
                {
                    "path": "typing.md",
                    "language": "markdown",
                    "content": "python typing annotations",
                }
            ],
        },
        content_type="application/json",
    )
    universal = client.post(
        "/api/records",
        data={
            "title": "Database migration rollback",
            "content": {
                "summary": "Database migration rollback.",
                "guidance": ["Review the completed change."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    unscoped = client.post(
        "/api/records",
        data={
            "title": "Unscoped database policy",
            "content": {
                "summary": "Belongs to a different project.",
                "applies_when": ["database migration"],
                "guidance": ["This guidance must not leak across projects."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    assert {database.status_code, python.status_code, universal.status_code, unscoped.status_code} == {201}

    python_project(tmp_path)
    project = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()["project"]
    replaced = client.put(
        f"/api/projects/{project['id']}/guidance-scopes",
        data={"record_ids": [universal.json()["id"], database.json()["id"], python.json()["id"]]},
        content_type="application/json",
    )

    assert replaced.status_code == 200
    assert [scope["record_id"] for scope in replaced.json()] == [
        universal.json()["id"],
        database.json()["id"],
        python.json()["id"],
    ]
    assert [scope["position"] for scope in replaced.json()] == [1, 2, 3]
    assert client.get(f"/api/projects/{project['id']}/guidance-scopes").json() == replaced.json()

    corpus = (
        ("database migration rollback", database.json()["id"]),
        ("python typing annotations", python.json()["id"]),
    )
    for task, expected_id in corpus:
        response = client.post(
            "/api/projects/workspace-contexts",
            data={"root": str(tmp_path), "task": task},
            content_type="application/json",
        )

        assert response.status_code == 200
        guidance_ids = [guidance["id"] for guidance in response.json()["guidance"]]
        assert guidance_ids == [dependencies["record_id"], expected_id, universal.json()["id"]]
        assert unscoped.json()["id"] not in guidance_ids
        assert [item["reason"] for item in response.json()["receipt"]["items"]] == [
            "operating-contract",
            "task-applicable",
            "project-default",
        ]


@override_settings(RECORDS_EMBEDDINGS_ENABLED=False)
@pytest.mark.django_db
def test_routes_optional_guidance_by_fallback_order_within_budget(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    first = client.post(
        "/api/records",
        data={
            "title": "First fallback",
            "content": {
                "summary": "a" * 1800,
                "guidance": ["Keep this complete."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    second = client.post(
        "/api/records",
        data={
            "title": "Second fallback",
            "content": {
                "summary": "b" * 3000,
                "guidance": ["This whole record exceeds the remaining budget."],
            },
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    assert first.status_code == 201
    assert second.status_code == 201

    python_project(tmp_path)
    project = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()["project"]
    scoped = client.put(
        f"/api/projects/{project['id']}/guidance-scopes",
        data={"record_ids": [first.json()["id"], second.json()["id"]]},
        content_type="application/json",
    )
    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Any task without ranking support"},
        content_type="application/json",
    )

    assert scoped.status_code == 200
    assert response.status_code == 200
    assert [guidance["id"] for guidance in response.json()["guidance"]] == [
        dependencies["record_id"],
        first.json()["id"],
    ]
    assert response.json()["guidance"][1]["summary"] == "a" * 1800
    assert response.json()["receipt"]["coverage"] == {
        "status": "partial",
        "selected_count": 2,
        "omitted_count": 1,
        "diagnostic_count": 0,
    }
    assert response.json()["receipt"]["omissions"] == [
        {
            "code": "optional-budget-exhausted",
            "guidance_ids": [second.json()["id"]],
            "message": "Supplemental guidance was omitted because the workspace-context budget was exhausted.",
        }
    ]
    assert response.json()["receipt"]["stop_condition"] == "resolve-context-gaps"


@pytest.mark.django_db
def test_protects_guidance_published_in_an_operating_contract(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    )
    deleted = client.delete(f"/api/records/{dependencies['record_id']}")

    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )

    assert deleted.status_code == 422
    assert deleted.json() == {"detail": "A record published in an operating contract cannot be deleted."}
    assert response.status_code == 200
    assert response.json()["readiness"] == "ready"
    assert response.json()["receipt"]["diagnostics"] == []


@pytest.mark.django_db
def test_marks_stale_guidance_revision_incomplete(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    )
    revised = client.put(
        f"/api/records/categories/{dependencies['category_id']}/content-schema",
        data={"content_schema": {"type": "object", "required": ["summary"]}},
        content_type="application/json",
    )

    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )

    assert revised.status_code == 200
    assert response.status_code == 200
    assert response.json()["readiness"] == "incomplete"
    assert response.json()["guidance"][0]["schema_revision"] == 1
    assert response.json()["guidance"][0]["current_schema_revision"] == 2
    assert response.json()["receipt"]["diagnostics"] == [
        {
            "code": "guidance_revision_stale",
            "message": "Bound guidance uses an obsolete category schema revision. Review and republish it.",
            "guidance_ids": [dependencies["record_id"]],
        }
    ]


@pytest.mark.django_db
def test_reports_conflicting_guidance_authority(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    first = client.put(
        f"/api/records/{dependencies['record_id']}",
        data={
            "title": "Project context",
            "content": {"authority": "project-policy"},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    second = client.post(
        "/api/records",
        data={
            "title": "Conflicting project context",
            "content": {"authority": "project-policy"},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] = [first["id"], second["id"]]
    client.post("/api/projects", data=payload, content_type="application/json")

    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )
    resolution = client.post(
        "/api/projects/workspace-resolutions",
        data={"root": str(tmp_path)},
        content_type="application/json",
    ).json()
    project = resolution["project"]
    workspace = resolution["workspace"]
    health = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")

    assert response.status_code == 200
    assert response.json()["readiness"] == "conflicted"
    assert response.json()["receipt"]["diagnostics"] == [
        {
            "code": "guidance_authority_conflict",
            "message": "Multiple bound guidance records claim authority 'project-policy'. Bind one effective source.",
            "guidance_ids": sorted([first["id"], second["id"]]),
        }
    ]
    assert health.json()["healthy"] is False
    assert [finding["rule"] for finding in health.json()["failures"]] == ["authority-conflict"]


@pytest.mark.django_db
def test_marks_changed_published_guidance_incomplete(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    second = client.post(
        "/api/records",
        data={
            "title": "Additional project context",
            "content": {},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] = [dependencies["record_id"], second["id"]]
    client.post("/api/projects", data=payload, content_type="application/json")
    changed = client.put(
        f"/api/records/{second['id']}",
        data={
            "title": "Changed project context",
            "content": {},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )

    response = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )

    assert changed.status_code == 200
    assert response.status_code == 200
    assert response.json()["readiness"] == "incomplete"
    assert response.json()["receipt"]["diagnostics"] == [
        {
            "code": "guidance_revision_changed",
            "message": "Published operating-contract guidance has changed. Publish a new contract revision.",
            "guidance_ids": [second["id"]],
        }
    ]


@pytest.mark.django_db
def test_updates_registered_project(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    created = client.post("/api/projects", data=payload, content_type="application/json")
    assert created.status_code == 201
    project = created.json()["project"]

    update = {
        "title": "Renamed project",
        "stack": payload["discovery"]["stack"],
        "boundaries_yaml": payload["boundaries_yaml"],
        "shape_yaml": UNHEALTHY_SHAPE_YAML,
        "scaffolding_id": payload["scaffolding_id"],
    }
    updated = client.put(
        f"/api/projects/{project['id']}",
        data=update,
        content_type="application/json",
    )

    assert updated.status_code == 200
    assert updated.json() == {**project, "title": "Renamed project"}
    assert client.get(f"/api/projects/{project['id']}").json() == updated.json()
    configurations = client.get(f"/api/projects/{project['id']}/architecture-configurations")
    assert configurations.status_code == 200
    references = configurations.json()
    assert len(references) == 1
    assert references[0]["project_id"] == project["id"]
    configuration = client.get(f"/api/projects/{project['id']}/architecture-configurations/{references[0]['id']}")
    assert configuration.status_code == 200
    assert configuration.json() == {
        "id": references[0]["id"],
        "project_id": project["id"],
        "revision": references[0]["revision"],
        "boundaries_yaml": BOUNDARIES_YAML,
        "shape_yaml": UNHEALTHY_SHAPE_YAML,
    }


@pytest.mark.django_db
def test_reads_revision_pinned_architecture_configuration_content(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    project_id = resolution["project"]["id"]
    reference = client.get(f"/api/projects/{project_id}/architecture-configurations").json()[0]

    response = client.get(
        f"/api/projects/{project_id}/architecture-configurations/{reference['id']}/content",
        data={
            "document": "boundaries_yaml",
            "expected_revision": reference["revision"],
            "offset": 0,
            "limit": 12,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "project_id": project_id,
        "configuration_id": reference["id"],
        "revision": reference["revision"],
        "document": "boundaries_yaml",
        "offset": 0,
        "limit": 12,
        "total_characters": len(BOUNDARIES_YAML),
        "content": BOUNDARIES_YAML[:12],
        "has_more": True,
        "next_offset": 12,
    }

    stale = client.get(
        f"/api/projects/{project_id}/architecture-configurations/{reference['id']}/content",
        data={
            "document": "boundaries_yaml",
            "expected_revision": "stale",
            "offset": 0,
            "limit": 12,
        },
    )
    assert stale.status_code == 422
    assert stale.json() == {"detail": "Architecture configuration changed; get it again before reading content."}

    for offset, limit, detail in (
        (-1, 12, "Architecture configuration content offset is outside the document."),
        (0, 1025, "Architecture configuration content limit must be between 1 and 1024."),
    ):
        invalid = client.get(
            f"/api/projects/{project_id}/architecture-configurations/{reference['id']}/content",
            data={
                "document": "boundaries_yaml",
                "expected_revision": reference["revision"],
                "offset": offset,
                "limit": limit,
            },
        )
        assert invalid.status_code == 422
        assert invalid.json() == {"detail": detail}


@pytest.mark.django_db
def test_generates_project_source_from_associated_scaffolding(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    target = tmp_path / "generated" / "src" / "package" / "__init__.py"
    target.parent.mkdir(parents=True)
    target.write_text("existing", encoding="utf-8")

    response = client.post(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations",
        data={"destination": "generated", "parameters": {}},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"files": ["generated/src/package/__init__.py"]}
    assert target.read_text(encoding="utf-8") == ""


@pytest.mark.django_db
def test_generation_respects_create_if_missing(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    scaffolding = client.get(f"/api/scaffoldings/{dependencies['scaffolding_id']}").json()
    scaffolding["spec"]["templates"][0]["write_mode"] = "create_if_missing"
    updated = client.put(
        f"/api/scaffoldings/{dependencies['scaffolding_id']}",
        data=scaffolding,
        content_type="application/json",
    )
    assert updated.status_code == 200
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    target = tmp_path / "generated" / "src" / "package" / "__init__.py"
    target.parent.mkdir(parents=True)
    target.write_text("existing", encoding="utf-8")

    response = client.post(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations",
        data={"destination": "generated", "parameters": {}},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Destination already contains: generated/src/package/__init__.py"}
    assert target.read_text(encoding="utf-8") == "existing"


@pytest.mark.django_db
def test_generation_rejects_destination_outside_project_root(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    outside = tmp_path.parent / f"{tmp_path.name}-outside"

    response = client.post(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/source-generations",
        data={"destination": f"../{outside.name}", "parameters": {}},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Generation destination escapes the project root."}
    assert not outside.exists()


@pytest.mark.django_db
def test_get_project_returns_not_found(client: Client) -> None:
    response = client.get("/api/projects/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


@pytest.mark.django_db
def test_update_project_returns_not_found(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)

    response = client.put(
        "/api/projects/missing",
        data={
            "title": "Missing project",
            "stack": discover(client, tmp_path)["stack"],
            "boundaries_yaml": BOUNDARIES_YAML,
            "shape_yaml": HEALTHY_SHAPE_YAML,
            "scaffolding_id": dependencies["scaffolding_id"],
        },
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


def test_siren_root_exposes_projects_collection(client: Client) -> None:
    response = client.get("/siren/", headers={"accept": "application/vnd.siren+json"})

    assert response.status_code == 200
    assert {link["href"] for link in response.json()["links"]} >= {
        "http://testserver/siren/projects",
    }


@pytest.mark.django_db
def test_registration_rejects_missing_scaffolding(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["scaffolding_id"] = "missing"

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


@pytest.mark.django_db
def test_registration_rejects_missing_record(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] = ["missing"]

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json() == {"detail": "Operating contract guidance must reference existing records."}


@pytest.mark.django_db
def test_registration_rejects_duplicate_record_bindings(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] *= 2

    response = client.post("/api/projects", data=payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json() == {"detail": "An operating contract revision cannot reference guidance more than once."}


@pytest.mark.django_db
def test_registration_rejects_duplicate_project_root(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    created = client.post("/api/projects", data=payload, content_type="application/json")
    assert created.status_code == 201

    duplicate = client.post("/api/projects", data=payload, content_type="application/json")

    assert duplicate.status_code == 422
    assert duplicate.json() == {"detail": f"Workspace root is already bound: {tmp_path}"}


@pytest.mark.django_db
def test_failed_registration_does_not_reserve_project_root(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    payload["record_ids"] = [dependencies["record_id"], "missing"]

    failed = client.post("/api/projects", data=payload, content_type="application/json")
    assert failed.status_code == 422

    payload["record_ids"] = [dependencies["record_id"]]
    retried = client.post("/api/projects", data=payload, content_type="application/json")

    assert retried.status_code == 201


@pytest.mark.django_db
def test_health_contains_only_gating_reports(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    created = client.post("/api/projects", data=payload, content_type="application/json")
    assert created.status_code == 201
    resolution = created.json()

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 200
    assert response.json()["healthy"] is True
    assert response.json()["outcome"] == "healthy"
    assert response.json()["reports"]
    assert all(report["failure_count"] == 0 for report in response.json()["reports"])
    guidance_report = next(report for report in response.json()["reports"] if report["id"] == "guidance-graph")
    assert guidance_report["advisory_count"] == 0


@pytest.mark.django_db
def test_health_reports_malformed_guidance_graph_and_blocks_ready_context(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    supplemental = client.post(
        "/api/records",
        data={
            "title": "Python refinement",
            "content": {"authority": "unrelated:python", "guidance": ["Keep typing strict."]},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    outside = client.post(
        "/api/records",
        data={
            "title": "Outside guidance",
            "content": {"guidance": ["This record is not effective for the project."]},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    project = resolution["project"]
    workspace = resolution["workspace"]
    scoped = client.put(
        f"/api/projects/{project['id']}/guidance-scopes",
        data={"record_ids": [supplemental["id"]]},
        content_type="application/json",
    )
    relationships = client.put(
        f"/api/projects/{project['id']}/guidance-relationships",
        data={
            "relationships": [
                {
                    "source_record_id": dependencies["record_id"],
                    "target_record_id": supplemental["id"],
                    "kind": "refinement",
                },
                {
                    "source_record_id": supplemental["id"],
                    "target_record_id": dependencies["record_id"],
                    "kind": "prerequisite",
                },
                {
                    "source_record_id": dependencies["record_id"],
                    "target_record_id": outside["id"],
                    "kind": "containment",
                },
            ]
        },
        content_type="application/json",
    )

    health = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")
    context = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change Python typing"},
        content_type="application/json",
    )

    assert scoped.status_code == 200
    assert relationships.status_code == 200
    assert all(relationship["id"] for relationship in relationships.json())
    assert {relationship["project_id"] for relationship in relationships.json()} == {project["id"]}
    assert client.get(f"/api/projects/{project['id']}/guidance-relationships").json() == relationships.json()
    assert health.status_code == 200
    assert health.json()["healthy"] is False
    rules = {finding["rule"] for finding in health.json()["failures"]}
    assert {
        "ambiguous-entry-point",
        "dangling-relationship",
        "guidance-cycle",
        "invalid-refinement",
    } <= rules
    assert all(finding["related_ids"] for finding in health.json()["failures"])
    assert all(finding["remediation"] for finding in health.json()["failures"])
    assert context.status_code == 200
    assert context.json()["readiness"] == "incomplete"
    assert "guidance-cycle" in {diagnostic["code"] for diagnostic in context.json()["receipt"]["diagnostics"]}


@pytest.mark.django_db
def test_health_keeps_unreachable_oversized_optional_guidance_advisory(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    optional = client.post(
        "/api/records",
        data={
            "title": "Large optional guidance",
            "content": {"summary": "x" * 5000},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    ).json()
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    project = resolution["project"]
    workspace = resolution["workspace"]
    client.put(
        f"/api/projects/{project['id']}/guidance-scopes",
        data={"record_ids": [optional["id"]]},
        content_type="application/json",
    )

    response = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")

    assert response.status_code == 200
    assert response.json()["healthy"] is True
    assert response.json()["failures"] == []
    assert {finding["rule"] for finding in response.json()["advisories"]} == {
        "optional-budget-exceeded",
        "unreachable-guidance",
    }


@pytest.mark.django_db
def test_health_blocks_oversized_required_guidance(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    client.put(
        f"/api/records/{dependencies['record_id']}",
        data={
            "title": "Project context",
            "content": {"guidance": ["x" * 9000]},
            "category_id": dependencies["category_id"],
            "tag_ids": [dependencies["tag_id"]],
            "resources": [],
        },
        content_type="application/json",
    )
    python_project(tmp_path)
    resolution = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    project = resolution["project"]
    workspace = resolution["workspace"]

    health = client.get(f"/api/projects/{project['id']}/workspaces/{workspace['id']}/health-violations")
    context = client.post(
        "/api/projects/workspace-contexts",
        data={"root": str(tmp_path), "task": "Change project source safely"},
        content_type="application/json",
    )

    assert health.json()["healthy"] is False
    assert [finding["rule"] for finding in health.json()["failures"]] == ["guidance-oversized"]
    assert context.json()["readiness"] == "incomplete"
    assert "guidance-oversized" in {diagnostic["code"] for diagnostic in context.json()["receipt"]["diagnostics"]}


@pytest.mark.django_db
def test_health_fails_when_architecture_has_a_shape_violation(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(
        discover(client, tmp_path),
        dependencies,
        shape_yaml=UNHEALTHY_SHAPE_YAML,
    )
    created = client.post("/api/projects", data=payload, content_type="application/json")
    assert created.status_code == 201
    resolution = created.json()

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
    )

    assert response.status_code == 200
    assert response.json()["healthy"] is False
    assert response.json()["failure_count"] > 0


@pytest.mark.django_db
def test_insights_contains_only_non_gating_reports(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    payload = registration(discover(client, tmp_path), dependencies)
    created = client.post("/api/projects", data=payload, content_type="application/json")
    assert created.status_code == 201
    resolution = created.json()

    response = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights"
    )

    assert response.status_code == 200
    assert response.json()["reports"]
    assert response.json()["sections"]
    assert all("metadata" in report for report in response.json()["reports"])

    section = response.json()["sections"][0]
    page = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/pages",
        data={
            "path": section["path"],
            "expected_revision": response.json()["revision"],
            "offset": 0,
            "limit": 1,
        },
    )
    assert page.status_code == 200
    assert page.json()["project_id"] == resolution["project"]["id"]
    assert page.json()["workspace_id"] == resolution["workspace"]["id"]
    assert page.json()["revision"] == response.json()["revision"]
    assert page.json()["path"] == section["path"]
    assert page.json()["total"] == section["total"]
    assert len(page.json()["items"]) == 1

    stale = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/pages",
        data={"path": section["path"], "expected_revision": "stale", "offset": 0, "limit": 1},
    )
    assert stale.status_code == 422
    assert stale.json() == {"detail": "Project insights changed; read them again before requesting a page."}

    oversized = client.get(
        f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/pages",
        data={
            "path": section["path"],
            "expected_revision": response.json()["revision"],
            "offset": 0,
            "limit": 26,
        },
    )
    assert oversized.status_code == 422
    assert oversized.json() == {"detail": "Project insight page limit must be between 1 and 25."}


@pytest.mark.django_db
@pytest.mark.parametrize("report", ["health-violations", "insights"])
def test_reports_return_not_found_for_missing_project(client: Client, report: str) -> None:
    response = client.get(f"/api/projects/missing/workspaces/missing-workspace/{report}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/projects/discoveries", {}),
        ("/api/projects", {}),
        ("/api/projects", {"discovery": {"root": "/tmp", "stack": {}}}),
    ],
)
def test_project_commands_reject_structurally_invalid_payloads(
    client: Client,
    path: str,
    payload: dict,
) -> None:
    response = client.post(path, data=payload, content_type="application/json")

    assert response.status_code == 422
