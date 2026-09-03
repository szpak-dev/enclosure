from pathlib import Path

import pytest
from django.test import Client

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
        "id": response.json()["id"],
        "root": str(tmp_path),
        "architecture_root": str(tmp_path),
        "language_id": "python",
        "language_version": "",
        "package_manager_id": "uv",
        "scaffolding_id": dependencies["scaffolding_id"],
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
    project = project_response.json()

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
    assert context.json()["diagnostics"][0]["code"] == "mandatory_contract_unconfigured"

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

    listed = client.get("/api/projects")
    found = client.post(
        "/api/projects/root-search-results",
        data={"root": str(tmp_path)},
        content_type="application/json",
    )
    fetched = client.get(f"/api/projects/{created.json()['id']}")

    assert listed.status_code == 200
    assert listed.json() == [{"id": created.json()["id"], "root": str(tmp_path)}]
    assert found.status_code == 200
    assert found.json() == {"id": created.json()["id"], "root": str(tmp_path)}
    assert fetched.status_code == 200
    assert fetched.json() == created.json()


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
    ).json()

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
        "authority": {
            "kind": "project-operating-contract",
            "id": f"project:{created['id']}:operating-contract",
            "revision": "1",
        },
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
        "diagnostics": [],
    }


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
    assert response.json()["diagnostics"] == []


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
    assert response.json()["diagnostics"] == [
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

    assert response.status_code == 200
    assert response.json()["readiness"] == "conflicted"
    assert response.json()["diagnostics"] == [
        {
            "code": "guidance_authority_conflict",
            "message": "Multiple bound guidance records claim authority 'project-policy'. Bind one effective source.",
            "guidance_ids": sorted([first["id"], second["id"]]),
        }
    ]


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
    assert response.json()["diagnostics"] == [
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

    payload["architecture_root"] = str(tmp_path / "src")
    payload["shape_yaml"] = UNHEALTHY_SHAPE_YAML
    updated = client.put(
        f"/api/projects/{created.json()['id']}",
        data=payload,
        content_type="application/json",
    )

    assert updated.status_code == 200
    assert updated.json() == {
        **created.json(),
        "architecture_root": str(tmp_path / "src"),
    }
    assert client.get(f"/api/projects/{created.json()['id']}").json() == updated.json()
    configurations = client.get(f"/api/projects/{created.json()['id']}/architecture-configurations")
    assert configurations.status_code == 200
    references = configurations.json()
    assert len(references) == 1
    assert references[0]["project_id"] == created.json()["id"]
    configuration = client.get(
        f"/api/projects/{created.json()['id']}/architecture-configurations/{references[0]['id']}"
    )
    assert configuration.status_code == 200
    assert configuration.json() == {
        "id": references[0]["id"],
        "project_id": created.json()["id"],
        "boundaries_yaml": BOUNDARIES_YAML,
        "shape_yaml": UNHEALTHY_SHAPE_YAML,
    }


@pytest.mark.django_db
def test_generates_project_source_from_associated_scaffolding(
    client: Client,
    dependencies: dict[str, str],
    tmp_path: Path,
) -> None:
    python_project(tmp_path)
    created = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    target = tmp_path / "generated" / "src" / "package" / "__init__.py"
    target.parent.mkdir(parents=True)
    target.write_text("existing", encoding="utf-8")

    response = client.post(
        f"/api/projects/{created['id']}/source-generations",
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
    created = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    target = tmp_path / "generated" / "src" / "package" / "__init__.py"
    target.parent.mkdir(parents=True)
    target.write_text("existing", encoding="utf-8")

    response = client.post(
        f"/api/projects/{created['id']}/source-generations",
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
    created = client.post(
        "/api/projects",
        data=registration(discover(client, tmp_path), dependencies),
        content_type="application/json",
    ).json()
    outside = tmp_path.parent / f"{tmp_path.name}-outside"

    response = client.post(
        f"/api/projects/{created['id']}/source-generations",
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
        data=registration(discover(client, tmp_path), dependencies),
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
    assert duplicate.json() == {"detail": "A project with this root already exists."}


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

    response = client.get(f"/api/projects/{created.json()['id']}/health-violations")

    assert response.status_code == 200
    assert response.json()["healthy"] is True
    assert response.json()["reports"]
    assert all("violations" in report for report in response.json()["reports"])
    assert all(not report["violations"] for report in response.json()["reports"])


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

    response = client.get(f"/api/projects/{created.json()['id']}/health-violations")

    assert response.status_code == 200
    assert response.json()["healthy"] is False
    assert any(report["violations"] for report in response.json()["reports"])


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

    response = client.get(f"/api/projects/{created.json()['id']}/insights")

    assert response.status_code == 200
    assert response.json()["reports"]
    assert all("violations" not in report for report in response.json()["reports"])


@pytest.mark.django_db
@pytest.mark.parametrize("report", ["health-violations", "insights"])
def test_reports_return_not_found_for_missing_project(client: Client, report: str) -> None:
    response = client.get(f"/api/projects/missing/{report}")

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
