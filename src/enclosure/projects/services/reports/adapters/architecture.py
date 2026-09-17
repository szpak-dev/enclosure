from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from modwire.application import ModwireApplication
from modwire.architecture.config.models.architecture_config import ArchitectureConfig
from wireup import injectable
from yaml import YAMLError

from enclosure.shared import SourceCodeService

from ....errors import ProjectsError


@injectable
@dataclass(frozen=True)
class ArchitectureAdapter:
    source_code: SourceCodeService

    def validate_yaml_config(self, boundaries_yaml: str, shape_yaml: str) -> None:
        self._configuration(ModwireApplication.create(), boundaries_yaml, shape_yaml)

    def generate_reports(
        self,
        architecture_root: str,
        language: str,
        boundaries_yaml: str,
        shape_yaml: str,
    ) -> tuple[dict[str, Any], ...]:
        application = ModwireApplication.create()
        config = self._configuration(application, boundaries_yaml, shape_yaml)
        code_map = self.source_code.read_map(Path(architecture_root), language, config.excluded_patterns)
        reports = application.analyze(code_map, config)
        return tuple(report.to_dict(mode="json") for report in reports)

    def _configuration(
        self,
        application: ModwireApplication,
        boundaries_yaml: str,
        shape_yaml: str,
    ) -> ArchitectureConfig:
        try:
            values = yaml.safe_load("\n".join((boundaries_yaml, shape_yaml)))
            return application.configure(values)
        except (ValueError, YAMLError) as error:
            raise ProjectsError(f"Invalid architecture configuration: {error}") from error
