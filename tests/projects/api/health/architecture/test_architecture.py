from pathlib import Path

import pytest
from django.test import Client

from ...support import (
    FLOW_BOUNDARIES_YAML,
    UNHEALTHY_SHAPE_YAML,
    accept_health_architecture,
    discover,
    python_project,
    registration,
)

pytestmark = [pytest.mark.django_db, pytest.mark.health]


class TestHealthArchitectureAttacks:
    @pytest.mark.django_db
    def test_health_rejects_a_project_without_an_accepted_architecture_contract(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": "Project health requires exactly one accepted project architecture contract."
        }

    @pytest.mark.django_db
    def test_health_blocks_closed_coverage_when_observer_support_is_incomplete(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution, coverage="closed")

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert response.status_code == 200, response.json()
        assert response.json()["healthy"] is False
        conformance = next(
            report for report in response.json()["reports"] if report["id"] == "architecture.conformance"
        )
        coverage = {item["assertion_kind"]: item for item in conformance["coverage"]}
        assert coverage["member"]["unverified"] == 1
        assert coverage["relationship"]["unverified"] == 1
        coverage_findings = [
            finding
            for finding in response.json()["failures"]
            if finding["kind"] == "conformance" and finding["evidence"]["kind"] == "coverage"
        ]
        assert {finding["evidence"]["assertion_kind"] for finding in coverage_findings} == {
            "member",
            "relationship",
        }
        assert {finding["target"] for finding in coverage_findings} == {"architecture-contract-unit:application"}

    @pytest.mark.django_db
    def test_health_reports_a_missing_declared_artifact(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        (tmp_path / "src" / "example" / "models.py").unlink()

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert response.status_code == 200, response.json()
        assert response.json()["healthy"] is False
        finding = next(
            finding
            for finding in response.json()["failures"]
            if finding["rule"] == "architecture.conformance.artifact" and finding["target"] == "artifact:models"
        )
        assert finding["finding_kind"] == "missing"
        assert finding["owner"] == "implementation"
        assert finding["expected"]["fields"] == {
            "path": "src/example/models.py",
            "artifact_kind": "file",
        }
        assert finding["observed"] == []

    @pytest.mark.django_db
    def test_health_closed_coverage_reports_an_unexpected_empty_directory(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution, coverage="closed")
        (tmp_path / "src" / "example" / "empty").mkdir()

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert response.status_code == 200, response.json()
        assert response.json()["healthy"] is False
        finding = next(
            finding
            for finding in response.json()["failures"]
            if finding["rule"] == "architecture.conformance.artifact"
            and finding["finding_kind"] == "unexpected"
            and finding["observed"][0]["fields"]["path"] == "src/example/empty"
        )
        assert finding["owner"] == "implementation"
        assert finding["observed"][0]["fields"]["artifact_kind"] == "directory"

    @pytest.mark.django_db
    def test_health_rejects_an_artifact_symlink_that_escapes_the_workspace(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution, coverage="closed")
        outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
        outside.write_text("class OutsideWorkspace:\n    pass\n", encoding="utf-8")
        (tmp_path / "src" / "example" / "escape.py").symlink_to(outside)

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": "Architecture artifact path escapes the workspace: 'src/example/escape.py'."
        }

    @pytest.mark.django_db
    def test_health_fails_when_architecture_has_a_shape_violation(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        payload = registration(
            discover(client, tmp_path),
            dependencies,
            shape_yaml=UNHEALTHY_SHAPE_YAML,
        )
        created = client.post("/api/projects", data=payload, content_type="application/json")
        assert created.status_code == 201
        resolution = created.json()
        accept_health_architecture(client, tmp_path, resolution)

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert response.status_code == 200
        assert response.json()["healthy"] is False
        assert response.json()["failure_count"] > 0
        assert response.json()["revision"]
        assert response.json()["failure_kind"] == "failure"
        assert response.json()["advisory_kind"] == "advisory"
        finding = next(finding for finding in response.json()["failures"] if finding["rule"] == "max_classes_per_file")
        assert finding == {
            "kind": "shape",
            "rule": "max_classes_per_file",
            "target": "app.py",
            "message": "file reports 1; configured limit is 0 in realm 'project'.",
            "next_action": "Review file in app.py: max_classes_per_file is 1; configured limit is 0.",
            "source_file": "app.py",
            "realm": "project",
            "symbol_kind": "file",
            "symbol_name": "",
            "actual": 1,
            "limit": 0,
        }
        page = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-findings",
            data={
                "kind": response.json()["failure_kind"],
                "expected_revision": response.json()["revision"],
                "offset": 0,
                "limit": 1,
            },
        )
        assert page.status_code == 200
        assert page.json()["revision"] == response.json()["revision"]
        assert page.json()["kind"] == "failure"
        assert page.json()["total"] == response.json()["failure_count"]
        assert len(page.json()["items"]) == 1

        stale = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-findings",
            data={"kind": "failure", "expected_revision": "stale", "offset": 0, "limit": 1},
        )
        assert stale.status_code == 422
        assert stale.json() == {"detail": "Project health changed; check it again before requesting findings."}


class TestHealthArchitectureInvariants:
    @pytest.mark.django_db
    def test_health_closed_coverage_preserves_an_internal_symlink_path(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution, coverage="closed")
        (tmp_path / "src" / "example" / "alias.py").symlink_to("service.py")

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert response.status_code == 200, response.json()
        assert response.json()["healthy"] is False
        finding = next(
            finding
            for finding in response.json()["failures"]
            if finding["rule"] == "architecture.conformance.artifact"
            and finding["finding_kind"] == "unexpected"
            and finding["observed"][0]["fields"]["path"] == "src/example/alias.py"
        )
        assert finding["observed"][0]["fields"]["artifact_kind"] == "file"

    @pytest.mark.django_db
    def test_health_preserves_exact_dependency_flow_location(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        (tmp_path / "uv.lock").write_text("", encoding="utf-8")
        (tmp_path / "example_tool.py").write_text(
            "from src.example_module import example_value\n",
            encoding="utf-8",
        )
        source = tmp_path / "src"
        source.mkdir()
        (source / "__init__.py").write_text("", encoding="utf-8")
        module = source / "example_module"
        module.mkdir(parents=True)
        (module / "__init__.py").write_text("", encoding="utf-8")
        (module / "example_value.py").write_text("EXAMPLE_VALUE = 1\n", encoding="utf-8")
        payload = registration(discover(client, tmp_path), dependencies)
        payload["boundaries_yaml"] = FLOW_BOUNDARIES_YAML
        resolution = client.post("/api/projects", data=payload, content_type="application/json").json()
        accept_health_architecture(client, tmp_path, resolution)

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert response.status_code == 200
        finding = next(
            finding
            for finding in response.json()["failures"]
            if finding["kind"] == "flow" and finding["target"] == "example_tool.py"
        )
        assert finding == {
            "kind": "flow",
            "rule": "boundary:unclassified",
            "target": "example_tool.py",
            "message": "tracked file does not match an architecture module",
            "next_action": (
                "Review dependency location example_tool.py at path index 0 against boundary:unclassified."
            ),
            "violation_type": "module-boundaries",
            "path": ["example_tool.py"],
            "violation_index": 0,
            "source_module": "",
            "target_module": "",
        }


class TestHealthArchitectureHappyPaths:
    @pytest.mark.django_db
    def test_health_returns_typed_conformance_evidence_for_mismatched_code(
        self,
        client: Client,
        dependencies: dict[str, str],
        tmp_path: Path,
    ) -> None:
        python_project(tmp_path)
        resolution = client.post(
            "/api/projects",
            data=registration(discover(client, tmp_path), dependencies),
            content_type="application/json",
        ).json()
        accept_health_architecture(client, tmp_path, resolution)
        (tmp_path / "src" / "example" / "service.py").write_text(
            "class ExampleService:\n"
            "    value: str\n\n"
            "    def execute(self, request: int) -> str:\n"
            "        return str(request)\n",
            encoding="utf-8",
        )

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert response.status_code == 200, response.json()
        assert response.json()["healthy"] is False
        finding = next(
            finding
            for finding in response.json()["failures"]
            if finding["kind"] == "conformance" and finding["rule"] == "architecture.conformance.member"
        )
        assert finding["finding_kind"] == "mismatched"
        assert finding["state"] == "fail"
        assert finding["owner"] == "implementation"
        assert finding["evidence"]["kind"] == "assertion"
        assert finding["evidence"]["diagram_evidence"]
        assert finding["evidence"]["implementation_evidence_ids"]
        assert finding["expected"]["kind"] == "member"
        assert finding["expected"]["fields"]["parameters"][0]["type"]["name"] == "String"
        assert finding["observed"][0]["kind"] == "member"
        assert finding["observed"][0]["fields"]["parameters"][0]["type"]["name"] == "Integer"
        assert len(finding["fingerprint"]) == 64

    @pytest.mark.django_db
    def test_health_returns_a_complete_attestation_for_an_aligned_project(
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
        accept_health_architecture(client, tmp_path, resolution)

        response = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-violations"
        )

        assert response.status_code == 200
        assert response.json()["healthy"] is True
        assert response.json()["outcome"] == "healthy"
        assert response.json()["reports"]
        assert all(report["failure_count"] == 0 for report in response.json()["reports"])
        conformance = next(
            report for report in response.json()["reports"] if report["id"] == "architecture.conformance"
        )
        assert {item["assertion_kind"] for item in conformance["coverage"]} == {
            "artifact",
            "classifier",
            "entity",
            "entity_field",
            "member",
            "relationship",
        }
        assert sum(item["passed"] for item in conformance["coverage"]) > 0
        assert all(item["failed"] == 0 and item["unverified"] == 0 for item in conformance["coverage"])
        attestation = response.json()["attestation"]
        assert attestation["digest_algorithm"] == "sha256"
        assert [component["kind"] for component in attestation["components"]] == [
            "contract",
            "implementation_evidence",
            "realization",
            "policies",
            "configuration",
            "schemas",
            "tools",
            "comparator",
            "findings",
        ]
        assert all(len(component["digest"]) == 64 for component in attestation["components"])
        assert len(attestation["digest"]) == 64
        assert len(response.json()["revision"]) == 64

        stale = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-attestation",
            data={"expected_revision": "stale"},
        )
        assert stale.status_code == 422
        assert stale.json() == {"detail": "Project health changed; check it again before requesting the attestation."}

        exact = client.get(
            f"/api/projects/{resolution['project']['id']}/workspaces/{resolution['workspace']['id']}/health-attestation",
            data={"expected_revision": response.json()["revision"]},
        )
        assert exact.status_code == 200
        assert exact.json() == attestation
        guidance_report = next(report for report in response.json()["reports"] if report["id"] == "guidance-graph")
        assert guidance_report["advisory_count"] == 0
