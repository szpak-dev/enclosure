import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def create_example_set(client: Client, title: str) -> dict[str, object]:
    response = client.post(
        "/api/diagram-sets",
        data={"title": title, "description": f"Example description for {title}."},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


def create_example_diagram(
    client: Client,
    diagram_set_id: object,
    title: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/diagram-sets/{diagram_set_id}/diagrams",
        data={"title": title, "kind": "flowchart"},
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()


def page_ids(client: Client, path: str, order_by: str, direction: str) -> list[object]:
    response = client.get(path, {"order_by": order_by, "direction": direction})
    assert response.status_code == 200
    assert response.json()["order_by"] == order_by
    assert response.json()["direction"] == direction
    return [item["id"] for item in response.json()["items"]]


def test_rejects_invalid_collection_ordering_without_changing_public_state() -> None:
    client = Client()
    diagram_set = create_example_set(client, "Example guarded set")
    diagram = create_example_diagram(client, diagram_set["id"], "Example guarded diagram")
    paths = (
        "/api/diagram-sets",
        "/api/diagrams",
        f"/api/diagram-sets/{diagram_set['id']}/diagrams",
    )
    pages_before = {path: client.get(path).json() for path in paths}
    diagram_before = client.get(f"/api/diagrams/{diagram['id']}").json()

    for path in paths:
        assert client.get(path, {"order_by": "example_missing"}).status_code == 422
        assert client.get(path, {"direction": "example_sideways"}).status_code == 422

    assert {path: client.get(path).json() for path in paths} == pages_before
    assert client.get(f"/api/diagrams/{diagram['id']}").json() == diagram_before


def test_global_and_nested_diagrams_follow_each_public_ordering() -> None:
    client = Client()
    diagram_set = create_example_set(client, "Example ordered set")
    created_first = create_example_diagram(client, diagram_set["id"], "Example zebra flow")
    created_second = create_example_diagram(client, diagram_set["id"], "Example alpha flow")
    updated_first_response = client.patch(
        f"/api/diagrams/{created_first['id']}",
        data={
            "expected_revision": created_first["revision"],
            "title": "Example zebra flow updated",
        },
        content_type="application/json",
    )
    assert updated_first_response.status_code == 200
    updated_first = updated_first_response.json()
    paths = (
        "/api/diagrams",
        f"/api/diagram-sets/{diagram_set['id']}/diagrams",
    )

    for path in paths:
        default_page = client.get(path)
        assert default_page.status_code == 200
        assert default_page.json()["order_by"] == "updated_at"
        assert default_page.json()["direction"] == "desc"
        assert [item["id"] for item in default_page.json()["items"]] == [
            updated_first["id"],
            created_second["id"],
        ]
        assert all("created_at" in item and "updated_at" in item for item in default_page.json()["items"])

        assert page_ids(client, path, "title", "asc") == [created_second["id"], updated_first["id"]]
        assert page_ids(client, path, "title", "desc") == [updated_first["id"], created_second["id"]]
        assert page_ids(client, path, "created_at", "asc") == [created_first["id"], created_second["id"]]
        assert page_ids(client, path, "created_at", "desc") == [created_second["id"], created_first["id"]]
        assert page_ids(client, path, "updated_at", "asc") == [created_second["id"], updated_first["id"]]
        assert page_ids(client, path, "updated_at", "desc") == [updated_first["id"], created_second["id"]]


def test_diagram_set_activity_comes_only_from_current_contained_diagrams() -> None:
    client = Client()
    empty_set = create_example_set(client, "Example empty set")
    first_set = create_example_set(client, "Example first active set")
    first_older = create_example_diagram(client, first_set["id"], "Example older diagram")
    first_newer = create_example_diagram(client, first_set["id"], "Example newer diagram")
    second_set = create_example_set(client, "Example second active set")
    second_diagram = create_example_diagram(client, second_set["id"], "Example latest diagram")

    metadata_update = client.put(
        f"/api/diagram-sets/{first_set['id']}",
        data={
            "title": "Example first active set updated",
            "description": "Example metadata change that is not diagram activity.",
        },
        content_type="application/json",
    )
    assert metadata_update.status_code == 200

    page = client.get("/api/diagram-sets").json()
    assert [item["id"] for item in page["items"]] == [
        second_set["id"],
        first_set["id"],
        empty_set["id"],
    ]
    first_summary = next(item for item in page["items"] if item["id"] == first_set["id"])
    assert first_summary["updated_at"] == first_newer["updated_at"]
    assert first_summary["updated_at"] != metadata_update.json()["updated_at"]

    renamed_response = client.patch(
        f"/api/diagrams/{first_older['id']}",
        data={
            "expected_revision": first_older["revision"],
            "title": "Example older diagram updated",
        },
        content_type="application/json",
    )
    assert renamed_response.status_code == 200
    renamed = renamed_response.json()
    after_activity = client.get("/api/diagram-sets").json()
    assert [item["id"] for item in after_activity["items"]] == [
        first_set["id"],
        second_set["id"],
        empty_set["id"],
    ]
    assert after_activity["items"][0]["updated_at"] == renamed["updated_at"]
    assert second_diagram["updated_at"] == after_activity["items"][1]["updated_at"]
