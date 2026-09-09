import pytest
from django.test import Client


@pytest.mark.django_db
def test_find_tags_returns_an_empty_collection() -> None:
    response = Client().get("/api/records/tags")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "has_more": False,
        "next_offset": 0,
        "limit": 50,
    }
