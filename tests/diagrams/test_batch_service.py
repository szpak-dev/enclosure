from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from enclosure.diagrams.errors import DiagramsError
from enclosure.diagrams.services.diagram_sets.service import DiagramSetService
from enclosure.diagrams.services.editing.service import DiagramEditingService
from enclosure.diagrams.services.mermaiden.service import MermaidenService
from enclosure.diagrams.services.repository import DiagramsRepository
from enclosure.diagrams.services.validation.service import DiagramValidationService


def test_batch_restores_snapshots_renders_and_persists_once() -> None:
    repository = Mock(spec=DiagramsRepository)
    mermaiden = Mock(spec=MermaidenService)
    validation = Mock(spec=DiagramValidationService)
    stored = SimpleNamespace(snapshot={"version": 4})
    in_memory = object()
    repository.get_diagram.return_value = stored
    repository.update_diagram.return_value = SimpleNamespace(id="diagram-1", revision=8)
    mermaiden.restore.return_value = in_memory
    mermaiden.snapshot.return_value = {"version": 4, "draft": False}
    mermaiden.render.return_value = "flowchart TD"
    validation.expected_revision.return_value = 7
    service = DiagramEditingService(
        repository=repository,
        diagram_sets=Mock(spec=DiagramSetService),
        mermaiden=mermaiden,
        validation=validation,
    )
    commands = (
        ("add_start", {"id": "start", "label": "Start"}),
        ("add_end", {"id": "end", "label": "End"}),
    )

    receipt = service.apply_batch("diagram-1", 7, commands)

    assert receipt == {"diagram_id": "diagram-1", "revision": 8, "applied_count": 2}
    mermaiden.restore.assert_called_once_with(stored.snapshot)
    assert mermaiden.apply.call_args_list == [
        call(in_memory, "add_start", {"id": "start", "label": "Start"}),
        call(in_memory, "add_end", {"id": "end", "label": "End"}),
    ]
    mermaiden.snapshot.assert_called_once_with(in_memory)
    mermaiden.render.assert_called_once_with(in_memory)
    repository.update_diagram.assert_called_once_with(
        "diagram-1",
        7,
        {"snapshot": {"version": 4, "draft": False}, "source": "flowchart TD"},
    )


def test_failed_batch_reports_the_command_and_does_not_persist() -> None:
    repository = Mock(spec=DiagramsRepository)
    mermaiden = Mock(spec=MermaidenService)
    repository.get_diagram.return_value = SimpleNamespace(snapshot={"version": 4})
    mermaiden.restore.return_value = object()
    mermaiden.apply.side_effect = [None, DiagramsError("Unknown command")]
    service = DiagramEditingService(
        repository=repository,
        diagram_sets=Mock(spec=DiagramSetService),
        mermaiden=mermaiden,
        validation=Mock(spec=DiagramValidationService),
    )

    with pytest.raises(
        DiagramsError,
        match="Diagram command batch failed at index 1 for operation 'missing': Unknown command",
    ):
        service.apply_batch(
            "diagram-1",
            1,
            (("add_start", {"id": "start", "label": "Start"}), ("missing", {})),
        )

    mermaiden.snapshot.assert_not_called()
    mermaiden.render.assert_not_called()
    repository.update_diagram.assert_not_called()
