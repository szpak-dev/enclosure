import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from mermaiden import Application
from pydantic import TypeAdapter


@pytest.fixture
def measure_svg(tmp_path: Path) -> Callable[[str], dict[str, list[str]]]:
    def measure(content: str) -> dict[str, list[str]]:
        svg = tmp_path / "example-diagram.svg"
        svg.write_text(content, encoding="utf-8")
        measured = subprocess.run(
            ["node", str(Path(__file__).parent / "fixtures/measure_svg.mjs"), str(svg)],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return TypeAdapter(dict[str, list[str]]).validate_json(measured.stdout)

    return measure


@pytest.fixture
def measure_snapshot_labels(
    measure_svg: Callable[[str], dict[str, list[str]]],
) -> Callable[[dict[str, object]], dict[str, list[str]]]:
    def measure(snapshot: dict[str, object]) -> dict[str, list[str]]:
        with Application.create() as application:
            report = application.validate_render(application.restore(snapshot))
        assert report.success
        return measure_svg(report.svg)

    return measure
