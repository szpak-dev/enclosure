import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


class TestProjectCommandAttacks:
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
        self,
        client: Client,
        path: str,
        payload: dict,
    ) -> None:
        response = client.post(path, data=payload, content_type="application/json")

        assert response.status_code == 422
