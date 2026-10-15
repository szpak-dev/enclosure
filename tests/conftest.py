import os
from collections.abc import Callable

import pytest
from django.conf import settings
from django.http.response import HttpResponseBase
from django.test import Client


@pytest.fixture(scope="session", autouse=True)
def isolate_project_health_cache(tmp_path_factory: pytest.TempPathFactory):
    cache_directory = tmp_path_factory.getbasetemp() / "health-cache"
    previous_environment = os.environ.get("PROJECT_HEALTH_CACHE_DIRECTORY")
    previous_setting = settings.PROJECT_HEALTH_CACHE_DIRECTORY
    settings.PROJECT_HEALTH_CACHE_DIRECTORY = str(cache_directory)
    os.environ["PROJECT_HEALTH_CACHE_DIRECTORY"] = str(cache_directory)
    try:
        yield
    finally:
        settings.PROJECT_HEALTH_CACHE_DIRECTORY = previous_setting
        if previous_environment is None:
            del os.environ["PROJECT_HEALTH_CACHE_DIRECTORY"]
        else:
            os.environ["PROJECT_HEALTH_CACHE_DIRECTORY"] = previous_environment


@pytest.fixture
def approve_operation() -> Callable[[Client, HttpResponseBase], None]:
    def approve(client: Client, response: HttpResponseBase) -> None:
        assert response.status_code == 409
        payload = response.json()
        approval_request_id = payload.get("approval_request_id") or payload["properties"]["approval_request_id"]
        approved = client.post(f"/api/security/approval-requests/{approval_request_id}/approvals")
        assert approved.status_code == 200
        approved_payload = approved.json()
        assert (approved_payload.get("state") or approved_payload["properties"]["state"]) == "approved"

    return approve
