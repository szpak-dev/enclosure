from dataclasses import dataclass
from typing import Any

import yaml
from django.conf import settings
from modwire.application import CacheOptions, ModwireApplication, ScanPolicy
from modwire.architecture.config.models.architecture_config import ArchitectureConfig
from wireup import injectable
from yaml import YAMLError

from ....errors import ProjectsError
from ..model import ArchitectureSource


@injectable
@dataclass(frozen=True)
class ArchitectureAdapter:
    def validate_yaml_config(self, boundaries_yaml: str, shape_yaml: str) -> None:
        self._configuration(ModwireApplication.create(), boundaries_yaml, shape_yaml)

    def generate_reports(
        self,
        source: ArchitectureSource,
    ) -> tuple[dict[str, Any], ...]:
        application = ModwireApplication.create()
        config = self._configuration(application, source.boundaries_yaml, source.shape_yaml)
        cache = self._cache_options(source.workspace_id)
        code_map = application.generate_queryable_map_cached(
            source.language,
            source.architecture_root,
            ScanPolicy(excluded_patterns=config.excluded_patterns),
            cache,
        )
        reports = application.analyze_cached(code_map, config, cache)
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

    def _cache_options(self, workspace_id: str) -> CacheOptions:
        return CacheOptions(
            directory=settings.MODWIRE_CACHE_DIRECTORY,
            namespace=workspace_id,
            max_bytes=settings.MODWIRE_CACHE_MAX_BYTES,
        )
