import pytest
from django.test import Client


@pytest.mark.django_db
def test_search_records_returns_an_empty_collection() -> None:
    response = Client().post(
        "/api/records/search-results",
        data={"query": "missing", "limit": 5},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == []
