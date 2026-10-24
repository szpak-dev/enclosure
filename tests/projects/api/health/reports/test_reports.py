from pathlib import Path

import pytest
from django.test import Client

from ...support import (
    discover,
    python_project,
    registration,
)

pytestmark = [pytest.mark.django_db, pytest.mark.health]


class TestHealthReportAttacks:
    @pytest.mark.django_db
    @pytest.mark.parametrize("report", ["health-violations", "insights"])
    def test_reports_return_not_found_for_missing_project(self, client: Client, report: str) -> None:
        response = client.get(f"/api/projects/missing/workspaces/missing-workspace/{report}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Resource not found."}


class TestHealthReportInvariants:
    @pytest.mark.django_db
    def test_insights_contains_only_non_gating_reports(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(discover(client, tmp_path), dependencies)
        created = client.post("/api/projects", data=payload, content_type="application/json")
        assert created.status_code == 201
        resolution = created.json()

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights"
        )

        assert response.status_code == 200
        assert response.json()["reports"]
        assert response.json()["report_count"] == len(response.json()["reports"])
        assert response.json()["sections"]
        assert all("metadata" in report for report in response.json()["reports"])

        section = response.json()["sections"][0]
        page = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/pages",
            data={
                "path": section["path"],
                "expected_revision": response.json()["revision"],
                "offset": 0,
                "limit": 1,
            },
        )
        assert page.status_code == 200
        assert page.json()["project_id"] == resolution["project"]["id"]
        assert page.json()["workspace_id"] == resolution["workspace"]["id"]
        assert page.json()["revision"] == response.json()["revision"]
        assert page.json()["path"] == section["path"]
        assert page.json()["total"] == section["total"]
        assert len(page.json()["items"]) == 1

        stale = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/pages",
            data={"path": section["path"], "expected_revision": "stale", "offset": 0, "limit": 1},
        )
        assert stale.status_code == 422
        assert stale.json() == {"detail": "Project insights changed; read them again before requesting a page."}

        oversized = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/pages",
            data={
                "path": section["path"],
                "expected_revision": response.json()["revision"],
                "offset": 0,
                "limit": 26,
            },
        )
        assert oversized.status_code == 422
        assert oversized.json()["detail"][0]["loc"] == ["query", "limit"]
        assert oversized.json()["detail"][0]["ctx"] == {"le": 25}

        content_path = (
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/insights/content"
        )
        section_offset = 0
        item_offset = 0
        recovered: dict[str, list[object]] = {}
        while True:
            content = client.get(
                content_path,
                data={
                    "expected_revision": response.json()["revision"],
                    "section_offset": section_offset,
                    "item_offset": item_offset,
                    "limit": 1,
                },
            )
            assert content.status_code == 200
            recovered.setdefault(content.json()["path"], []).extend(content.json()["items"])
            if not content.json()["has_more"]:
                break
            section_offset = content.json()["next_section_offset"]
            item_offset = content.json()["next_item_offset"]

        assert set(recovered) == {section["path"] for section in response.json()["sections"]}
        assert {path: len(items) for path, items in recovered.items()} == {
            section["path"]: section["total"] for section in response.json()["sections"]
        }

        stale_content = client.get(
            content_path,
            data={"expected_revision": "stale", "section_offset": 0, "item_offset": 0, "limit": 1},
        )
        assert stale_content.status_code == 422
        assert stale_content.json() == {
            "detail": "Project insights changed; read them again before requesting content."
        }
