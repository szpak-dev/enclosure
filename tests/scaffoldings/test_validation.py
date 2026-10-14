import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("payload", "location", "error_type"),
    (
        (
            {
                "language_id": "x" * 33,
                "name": "Example package",
                "description": "Example mechanically invalid language.",
                "spec": {"language": "python", "variables": [], "templates": []},
            },
            ["body", "body", "language_id"],
            "string_too_long",
        ),
        (
            {
                "language_id": "python",
                "name": "x" * 121,
                "description": "Example mechanically invalid name.",
                "spec": {"language": "python", "variables": [], "templates": []},
            },
            ["body", "body", "name"],
            "string_too_long",
        ),
        (
            {
                "language_id": "python",
                "name": "Example package",
                "description": "Example mechanically invalid variable type.",
                "spec": {
                    "language": "python",
                    "variables": [{"name": "example_value", "type": "mapping"}],
                    "templates": [],
                },
            },
            ["body", "body", "spec", "variables", 0, "type"],
            "literal_error",
        ),
        (
            {
                "language_id": "python",
                "name": "Example package",
                "description": "Example mechanically invalid write mode.",
                "spec": {
                    "language": "python",
                    "variables": [],
                    "templates": [{"path": "example.txt", "content": "example", "write_mode": "append"}],
                },
            },
            ["body", "body", "spec", "templates", 0, "write_mode"],
            "literal_error",
        ),
    ),
    ids=("language-bound", "name-bound", "variable-type", "write-mode"),
)
def test_mechanically_invalid_creation_leaves_the_catalogue_unchanged(
    payload: dict[str, object],
    location: list[str | int],
    error_type: str,
) -> None:
    client = Client()
    before = client.get("/api/scaffoldings", data={"offset": 0, "limit": 100}).json()

    response = client.post("/api/scaffoldings", data=payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == location
    assert response.json()["detail"][0]["type"] == error_type
    assert client.get("/api/scaffoldings", data={"offset": 0, "limit": 100}).json() == before


@pytest.mark.parametrize(
    ("spec", "detail"),
    (
        (
            {
                "language": "python",
                "variables": [{"name": "example-value", "type": "string"}],
                "templates": [],
            },
            "Scaffolding variable name must be a valid identifier: 'example-value'",
        ),
        (
            {
                "language": "python",
                "variables": [
                    {"name": "example_value", "type": "string"},
                    {"name": "example_value", "type": "integer"},
                ],
                "templates": [],
            },
            "Scaffolding variable names must be unique: example_value",
        ),
        (
            {
                "language": "python",
                "variables": [],
                "templates": [{"path": "../example.py", "content": "example", "write_mode": "overwrite"}],
            },
            "Invalid scaffolding template path '../example.py': "
            "Code package path contains an invalid segment: '../example.py'",
        ),
        (
            {
                "language": "python",
                "variables": [],
                "templates": [
                    {"path": "example.py", "content": "first", "write_mode": "overwrite"},
                    {"path": "example.py", "content": "second", "write_mode": "overwrite"},
                ],
            },
            "Scaffolding template paths must be unique: example.py",
        ),
        (
            {
                "language": "python",
                "variables": [],
                "templates": [
                    {"path": "example", "content": "first", "write_mode": "overwrite"},
                    {
                        "path": "example/value.py",
                        "content": "second",
                        "write_mode": "overwrite",
                    },
                ],
            },
            "Scaffolding template paths conflict as files and directories: example and example/value.py",
        ),
    ),
    ids=("variable-identity", "variable-uniqueness", "template-path", "template-uniqueness", "package-topology"),
)
def test_semantically_invalid_creation_leaves_the_catalogue_unchanged(
    spec: dict[str, object],
    detail: str,
) -> None:
    client = Client()
    before = client.get("/api/scaffoldings", data={"offset": 0, "limit": 100}).json()

    response = client.post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Example invalid package",
            "description": "Example semantic rejection.",
            "spec": spec,
        },
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    assert client.get("/api/scaffoldings", data={"offset": 0, "limit": 100}).json() == before


def test_rejected_creation_does_not_reserve_identity_and_the_corrected_request_recovers() -> None:
    client = Client()
    payload = {
        "language_id": "python",
        "name": "Example recovery package",
        "description": "Example create recovery.",
        "spec": {"language": "typescript", "variables": [], "templates": []},
    }

    rejected = client.post("/api/scaffoldings", data=payload, content_type="application/json")
    payload["spec"]["language"] = "python"
    recovered = client.post("/api/scaffoldings", data=payload, content_type="application/json")

    assert rejected.status_code == 422
    assert rejected.json() == {"detail": "Scaffolding language must match its specification language."}
    assert recovered.status_code == 201
    assert recovered.json()["name"] == "Example recovery package"


def test_rejected_update_preserves_the_complete_public_state_and_the_corrected_update_recovers() -> None:
    client = Client()
    payload = {
        "language_id": "python",
        "name": "Example update package",
        "description": "Example update invariant.",
        "spec": {
            "language": "python",
            "variables": [],
            "templates": [{"path": "example.py", "content": "example", "write_mode": "overwrite"}],
        },
    }
    created = client.post("/api/scaffoldings", data=payload, content_type="application/json")
    assert created.status_code == 201
    path = f"/api/scaffoldings/{created.json()['id']}"
    before = client.get(path).json()

    payload["spec"]["templates"] = [
        {"path": "example", "content": "first", "write_mode": "overwrite"},
        {"path": "example/value.py", "content": "second", "write_mode": "overwrite"},
    ]
    rejected = client.put(path, data=payload, content_type="application/json")
    after = client.get(path).json()

    payload["name"] = "Example recovered update"
    payload["spec"]["templates"] = [{"path": "example.py", "content": "recovered", "write_mode": "overwrite"}]
    recovered = client.put(path, data=payload, content_type="application/json")

    assert rejected.status_code == 422
    assert rejected.json() == {
        "detail": "Scaffolding template paths conflict as files and directories: example and example/value.py"
    }
    assert after == before
    assert recovered.status_code == 200
    assert recovered.json()["name"] == "Example recovered update"


def test_invalid_rendering_parameters_preserve_state_and_valid_values_for_every_type_recover() -> None:
    client = Client()
    created = client.post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Example typed rendering",
            "description": "Example rendering parameter contract.",
            "spec": {
                "language": "python",
                "variables": [
                    {"name": "example_string", "type": "string"},
                    {"name": "example_integer", "type": "integer"},
                    {"name": "example_number", "type": "number"},
                    {"name": "example_boolean", "type": "boolean"},
                    {"name": "example_array", "type": "array"},
                    {"name": "example_object", "type": "object"},
                ],
                "templates": [{"path": "example.txt", "content": "example", "write_mode": "overwrite"}],
            },
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    scaffolding_id = created.json()["id"]
    detail_path = f"/api/scaffoldings/{scaffolding_id}"
    rendering_path = f"{detail_path}/renderings"
    before = client.get(detail_path).json()

    rejected = client.post(
        rendering_path,
        data={
            "parameters": {
                "example_string": "example",
                "example_integer": 7,
                "example_number": 1.5,
                "example_boolean": True,
                "example_array": ["example"],
                "example_extra": "unexpected",
            }
        },
        content_type="application/json",
    )
    after = client.get(detail_path).json()
    recovered = client.post(
        rendering_path,
        data={
            "parameters": {
                "example_string": "example",
                "example_integer": 7,
                "example_number": 1.5,
                "example_boolean": True,
                "example_array": ["example"],
                "example_object": {"example": "value"},
            }
        },
        content_type="application/json",
    )

    assert rejected.status_code == 422
    assert rejected.json() == {
        "detail": "Invalid rendering parameters (missing: example_object; unexpected: example_extra)."
    }
    assert after == before
    assert recovered.status_code == 200
    assert recovered.json()["items"][0]["path"] == "example.txt"
    assert recovered.json()["items"][0]["preview"] == "example"
