from pathlib import Path

import pytest
from django.test import Client

from ..support import (
    python_project,
)

pytestmark = pytest.mark.django_db


class TestDiscoveryAttacks:
    @pytest.mark.django_db
    def test_discovery_rejects_missing_directory(self, client: Client, tmp_path: Path) -> None:
        missing = tmp_path / "missing"

        response = client.post(
            "/api/projects/discoveries",
            data={"root": str(missing)},
            content_type="application/json",
        )

        assert response.status_code == 422, response.json()
        assert response.json() == {"detail": f"Invalid project root: {missing}"}

    @pytest.mark.django_db
    def test_discovery_rejects_project_without_package_manager(self, client: Client, tmp_path: Path) -> None:
        response = client.post(
            "/api/projects/discoveries",
            data={"root": str(tmp_path)},
            content_type="application/json",
        )

        assert response.status_code == 422, response.json()
        assert response.json() == {"detail": "Package manager could not be recognized."}

    @pytest.mark.django_db
    def test_discovery_rejects_ambiguous_package_managers(self, client: Client, tmp_path: Path) -> None:
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


class TestDiscoveryHappyPaths:
    @pytest.mark.django_db
    def test_discovers_python_project_without_changing_its_root(self, client: Client, tmp_path: Path) -> None:
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
