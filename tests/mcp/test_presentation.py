from dataclasses import dataclass

from enclosure.mcp.services.bootstrap import AgentBootstrapService, BootstrapRepository
from enclosure.mcp.services.operations import SirenDocument
from enclosure.mcp.services.presentation import PresentationService
from enclosure.shared import TemplateService


@dataclass(frozen=True)
class ExampleBootstrapRepository(BootstrapRepository):
    def read(self) -> str:
        return "# Example bootstrap"


def test_preserves_malformed_specialized_documents_compatibly() -> None:
    document = SirenDocument(
        operation_id="get_workspace_context",
        document={"class": ["workspace-context"], "unexpected": "example-value"},
        is_error=False,
        classes=("workspace-context",),
        title="Example workspace context",
        detail="",
    )

    result = PresentationService(
        bootstrap=AgentBootstrapService(repository=ExampleBootstrapRepository()),
        templates=TemplateService(),
    ).present(document)

    assert result.is_error is False
    assert result.markdown == "Example workspace context"
    assert result.structured_content == document.document


def test_presents_advisory_health_without_turning_it_into_a_failure() -> None:
    document = SirenDocument(
        operation_id="check_project_health",
        document={
            "class": ["command-result"],
            "properties": {
                "healthy": True,
                "reports": [
                    {
                        "metadata": {
                            "id": "example.health",
                            "title": "Example health",
                        },
                        "violations": [],
                        "advisories": [
                            {
                                "source_id": "example_app.py",
                                "rule_name": "example-advisory",
                                "actual": 2,
                                "limit": 1,
                            }
                        ],
                    }
                ],
            },
        },
        is_error=False,
        classes=("command-result",),
        title="Example project health",
        detail="",
    )

    result = PresentationService(
        bootstrap=AgentBootstrapService(repository=ExampleBootstrapRepository()),
        templates=TemplateService(),
    ).present(document)

    assert result.is_error is False
    assert result.structured_content["status"] == "advisory"
    assert result.structured_content["failure_count"] == 0
    assert result.structured_content["advisory_count"] == 1
    assert "## Advisories" in result.markdown
