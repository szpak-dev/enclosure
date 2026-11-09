import json
from collections.abc import Callable, Iterator
from copy import deepcopy
from hashlib import sha256
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import Client

from ..support import create_architecture_contract_fixture


@pytest.fixture
def legacy_architecture(
    client: Client, dependencies: dict[str, str], tmp_path: Path
) -> Iterator[Callable[[bool], str]]:
    fixture = create_architecture_contract_fixture(client, dependencies, tmp_path)
    publication = fixture.publish_example_architecture()
    url = f"/api/projects/{fixture.project_id}/architecture-contract-publications/{publication['id']}"
    historical = json.loads(
        (Path(__file__).parents[3] / "diagrams/fixtures/mermaiden-13.1.0-architecture.json").read_text()
    )
    legacy = next(diagram for diagram in historical["diagrams"] if diagram["kind"] == "classDiagram")

    def evidence() -> str:
        output = StringIO()
        call_command("dumpdata", "projects.architecturecontractdiagram", stdout=output)
        return output.getvalue()

    original = json.loads(evidence())
    expected = evidence()

    def load(unknown_field: bool) -> str:
        nonlocal expected
        assert evidence() == expected
        documents = deepcopy(original)
        for document in documents:
            fields = document["fields"]
            if fields["kind"] != "classDiagram":
                continue
            snapshot = fields["snapshot"]
            snapshot["version"] = legacy["snapshot"]["version"]
            snapshot["configuration"] = deepcopy(legacy["snapshot"]["configuration"])
            if unknown_field:
                snapshot["configuration"]["fields"]["unexpected_option"] = True
            fields["snapshot_version"] = snapshot["version"]
            fields["registry_fingerprint"] = historical["registry_fingerprint"]
            fields["snapshot_digest"] = sha256(
                json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
            ).hexdigest()
        path = tmp_path / "legacy-architecture.json"
        path.write_text(json.dumps(documents))
        call_command("loaddata", str(path), verbosity=0)
        expected = evidence()
        return url

    yield load
    assert evidence() == expected
