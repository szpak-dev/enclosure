from collections.abc import Callable

import pytest
from django.http.response import HttpResponseBase
from django.test import Client


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
