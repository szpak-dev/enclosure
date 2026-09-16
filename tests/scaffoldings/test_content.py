import pytest
from django.test import Client


@pytest.mark.django_db
def test_reads_template_and_rendered_content_by_exact_revision() -> None:
    client = Client()
    source = "value={{ name }}\n" * 48
    created = client.post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Bounded content",
            "description": "Exercises focused content reads.",
            "spec": {
                "language": "python",
                "variables": [{"name": "name", "type": "string"}],
                "templates": [
                    {
                        "path": "generated.txt.jinja",
                        "content": source,
                        "write_mode": "overwrite",
                    }
                ],
            },
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    scaffolding = created.json()
    manifest = scaffolding["spec"]["templates"][0]

    first = client.get(
        f"/api/scaffoldings/{scaffolding['id']}/template-content",
        data={
            "path": manifest["path"],
            "expected_revision": manifest["revision"],
            "offset": 0,
            "limit": 512,
        },
    )
    second = client.get(
        f"/api/scaffoldings/{scaffolding['id']}/template-content",
        data={
            "path": manifest["path"],
            "expected_revision": manifest["revision"],
            "offset": first.json()["next_offset"],
            "limit": 512,
        },
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["has_more"] is True
    assert first.json()["content"] + second.json()["content"] == source

    rendering = client.post(
        f"/api/scaffoldings/{scaffolding['id']}/renderings",
        data={"parameters": {"name": "example"}, "offset": 0, "limit": 10},
        content_type="application/json",
    )
    assert rendering.status_code == 200
    rendered_manifest = rendering.json()["items"][0]
    assert len(rendered_manifest["preview"]) <= 256

    rendered = client.post(
        f"/api/scaffoldings/{scaffolding['id']}/rendered-file-content",
        data={
            "parameters": {"name": "example"},
            "path": rendered_manifest["path"],
            "expected_revision": rendered_manifest["revision"],
            "offset": 0,
            "limit": 512,
        },
        content_type="application/json",
    )
    assert rendered.status_code == 200
    assert rendered.json()["content"].startswith("value=example")


@pytest.mark.django_db
def test_focused_reads_reject_stale_revisions_and_unknown_paths() -> None:
    client = Client()
    created = client.post(
        "/api/scaffoldings",
        data={
            "language_id": "python",
            "name": "Revision checks",
            "description": "Exercises immutable read identity.",
            "spec": {
                "language": "python",
                "variables": [],
                "templates": [{"path": "value.txt", "content": "value", "write_mode": "overwrite"}],
            },
        },
        content_type="application/json",
    ).json()
    path = f"/api/scaffoldings/{created['id']}/template-content"
    revision = created["spec"]["templates"][0]["revision"]

    stale = client.get(
        path,
        data={"path": "value.txt", "expected_revision": "0" * 64, "offset": 0, "limit": 5},
    )
    missing = client.get(
        path,
        data={"path": "missing.txt", "expected_revision": revision, "offset": 0, "limit": 5},
    )

    assert stale.status_code == 422
    assert "revision changed" in stale.json()["detail"]
    assert missing.status_code == 422
    assert missing.json()["detail"] == "Scaffolding template does not exist: missing.txt"
