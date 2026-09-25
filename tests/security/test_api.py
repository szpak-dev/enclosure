import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def create_diagram_set(client: Client, title: str) -> dict[str, object]:
    response = client.post(
        "/api/diagram-sets",
        data={"title": title, "description": f"Diagrams for {title}."},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


def request_deletion(client: Client, diagram_set_id: object):
    return client.delete(f"/api/diagram-sets/{diagram_set_id}")


def test_rejects_an_invalid_bearer_token() -> None:
    response = Client().get(
        "/api/",
        headers={"Authorization": "Bearer example-invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication is required.",
        "reason_code": "invalid_bearer_token",
    }


def test_approval_is_exactly_scoped_and_consumed_once() -> None:
    client = Client()
    first = create_diagram_set(client, "Example first set")
    second = create_diagram_set(client, "Example second set")

    first_attempt = request_deletion(client, first["id"])
    second_attempt = request_deletion(client, second["id"])

    assert first_attempt.status_code == 409
    assert second_attempt.status_code == 409
    assert first_attempt.json()["reason_code"] == "destructive_approval_required"
    assert second_attempt.json()["reason_code"] == "destructive_approval_required"
    assert first_attempt.json()["approval_request_id"] != second_attempt.json()["approval_request_id"]

    approval_request_id = first_attempt.json()["approval_request_id"]
    approval_request = client.get(f"/api/security/approval-requests/{approval_request_id}")

    assert approval_request.status_code == 200
    assert approval_request.json()["operation_id"] == "DELETE api/diagram-sets/<diagram_set_id>"
    assert approval_request.json()["state"] == "pending"

    approved = client.post(f"/api/security/approval-requests/{approval_request_id}/approvals")
    deleted = request_deletion(client, first["id"])
    replayed = request_deletion(client, first["id"])

    assert approved.status_code == 200
    assert approved.json()["state"] == "approved"
    assert deleted.status_code == 204
    assert replayed.status_code == 409
    assert replayed.json()["reason_code"] == "destructive_approval_required"


def test_rejection_keeps_the_resource_and_allows_a_new_request() -> None:
    client = Client()
    diagram_set = create_diagram_set(client, "Example rejected set")
    first_attempt = request_deletion(client, diagram_set["id"])
    approval_request_id = first_attempt.json()["approval_request_id"]

    rejected = client.post(f"/api/security/approval-requests/{approval_request_id}/rejections")
    second_attempt = request_deletion(client, diagram_set["id"])
    fetched = client.get(f"/api/diagram-sets/{diagram_set['id']}")

    assert rejected.status_code == 200
    assert rejected.json()["state"] == "rejected"
    assert second_attempt.status_code == 409
    assert second_attempt.json()["approval_request_id"] != approval_request_id
    assert fetched.status_code == 200


def test_audit_events_report_authorization_and_execution_without_request_content() -> None:
    client = Client()
    diagram_set = create_diagram_set(client, "Example audited set")
    first_attempt = request_deletion(client, diagram_set["id"])
    approval_request_id = first_attempt.json()["approval_request_id"]
    client.post(f"/api/security/approval-requests/{approval_request_id}/approvals")
    deleted = request_deletion(client, diagram_set["id"])

    response = client.get("/api/security/audit-events", data={"limit": 100})

    assert deleted.status_code == 204
    assert response.status_code == 200
    events = [
        event
        for event in response.json()["items"]
        if event["operation_id"] == "DELETE api/diagram-sets/<diagram_set_id>"
    ]
    assert {(event["phase"], event["reason_code"]) for event in events} == {
        ("authorization", "destructive_approval_required"),
        ("authorization", "approval_consumed"),
        ("execution", "execution_succeeded"),
    }
    assert all(event["safe_metadata"] == {"classification": "destructive", "method": "DELETE"} for event in events)
    assert all("Example audited set" not in str(event) for event in events)
