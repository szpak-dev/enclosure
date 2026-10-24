import pytest
from django.test import Client

from .support import ArchivedArchitectureApplicationFactory


@pytest.fixture
def archived_architecture_application(client: Client) -> ArchivedArchitectureApplicationFactory:
    return ArchivedArchitectureApplicationFactory(client)
