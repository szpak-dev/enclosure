import pytest
from django.test import Client


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/api/records/missing",
        "/api/records/categories/missing",
        "/api/records/tags/missing",
    ],
)
def test_missing_records_return_not_found(path: str) -> None:
    response = Client().get(path)

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}


@pytest.mark.django_db
def test_update_schema_of_missing_category_returns_not_found() -> None:
    response = Client().put(
        "/api/records/categories/missing/content-schema",
        data={"content_schema": {"type": "object"}},
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found."}
