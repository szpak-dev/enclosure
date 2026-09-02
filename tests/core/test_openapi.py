import re
from collections.abc import Iterator

from django.test import Client

SNAKE_CASE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
HTTP_METHODS = {"delete", "get", "patch", "post", "put"}


def find_operation_ids(value: object) -> Iterator[object]:
    if isinstance(value, dict):
        if "operationId" in value:
            yield value["operationId"]
        for child in value.values():
            yield from find_operation_ids(child)
    elif isinstance(value, list):
        for child in value:
            yield from find_operation_ids(child)


def test_api_operation_ids_are_unique_snake_case() -> None:
    schema = Client().get("/api/openapi.json").json()
    operation_ids = list(find_operation_ids(schema))

    assert operation_ids
    assert all(isinstance(operation_id, str) and SNAKE_CASE.fullmatch(operation_id) for operation_id in operation_ids)
    assert len(operation_ids) == len(set(operation_ids))


def test_api_operations_and_fields_are_documented() -> None:
    schema = Client().get("/api/openapi.json").json()
    operations = [
        operation for path in schema["paths"].values() for method, operation in path.items() if method in HTTP_METHODS
    ]
    parameters = [parameter for operation in operations for parameter in operation.get("parameters", [])]
    fields = [
        field
        for component in schema["components"]["schemas"].values()
        for field in component.get("properties", {}).values()
    ]

    assert all(operation.get("summary") and operation.get("description") for operation in operations)
    assert all(parameter.get("description") for parameter in parameters)
    assert all(field.get("description") for field in fields)


def test_diagram_interactions_are_not_advertised() -> None:
    schema = Client().get("/api/openapi.json").json()

    assert "/api/diagrams/{diagram_id}/interactions" not in schema["paths"]
    assert "update_diagram_interactions" not in set(find_operation_ids(schema))
