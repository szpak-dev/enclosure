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
        "record_id": record.json()["id"],
        "scaffolding_id": scaffolding.json()["id"],
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
        "boundaries_yaml": BOUNDARIES_YAML,
        "shape_yaml": HEALTHY_SHAPE_YAML,
        "scaffolding_id": dependencies["scaffolding_id"],
    }


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
    fetched = client.get(f"/api/projects/{created.json()['id']}")

    assert listed.status_code == 200
    assert listed.json() == [created.json()]
    assert fetched.status_code == 200
    assert fetched.json() == created.json()


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
        "shape_yaml": UNHEALTHY_SHAPE_YAML,
    }
    assert client.get(f"/api/projects/{created.json()['id']}").json() == updated.json()


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

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


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
    assert response.json() == {"detail": "A project cannot bind the same record more than once."}


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
    assert failed.status_code == 404

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
