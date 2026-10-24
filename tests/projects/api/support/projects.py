from hashlib import sha256
from pathlib import Path

from django.test import Client

from .configuration import BOUNDARIES_YAML, HEALTHY_SHAPE_YAML


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


def distinguish_project_source(root: Path, name: str) -> None:
    identity = sha256(root.as_posix().encode("utf-8")).hexdigest()[:16]
    (root / "identity.py").write_text(f"class {name}{identity}:\n    pass\n", encoding="utf-8")
