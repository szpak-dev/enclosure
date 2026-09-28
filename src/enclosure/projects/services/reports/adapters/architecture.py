from dataclasses import dataclass
from typing import cast

import yaml
from django.conf import settings
from modwire.application import CacheOptions, ModwireApplication, ScanPolicy
from modwire.architecture.config.models.architecture_config import ArchitectureConfig
from pydantic import JsonValue
from wireup import injectable
from yaml import YAMLError

from enclosure.diagnostics.services import CacheDiagnosticsContext

from ....errors import ProjectsError
from ..model import ArchitectureObservation, ArchitectureSource


@injectable
@dataclass(frozen=True)
class ArchitectureAdapter:
    cache_diagnostics: CacheDiagnosticsContext

    def validate_yaml_config(self, boundaries_yaml: str, shape_yaml: str) -> None:
        self.build_configuration(ModwireApplication.create(), boundaries_yaml, shape_yaml)

    def generate_reports(
        self,
        source: ArchitectureSource,
    ) -> tuple[dict[str, JsonValue], ...]:
        application = ModwireApplication.create()
        config = self.build_configuration(application, source.boundaries_yaml, source.shape_yaml)
        cache = self.cache_options(source.workspace_id)
        code_map = application.generate_queryable_map_cached_with_diagnostics(
            source.language,
            source.architecture_root,
            ScanPolicy(excluded_patterns=config.excluded_patterns),
            cache,
        )
        self.cache_diagnostics.record(code_map.outcomes)
        reports = application.analyze_cached_with_diagnostics(code_map.value, config, cache)
        self.cache_diagnostics.record(reports.outcomes)
        return tuple(cast(dict[str, JsonValue], report.to_dict(mode="json")) for report in reports.value)

    def observe(self, source: ArchitectureSource) -> ArchitectureObservation:
        application = ModwireApplication.create()
        config = self.build_configuration(application, source.boundaries_yaml, source.shape_yaml)
        cache = self.cache_options(source.workspace_id)
        code_map = application.generate_queryable_map_cached_with_diagnostics(
            source.language,
            source.architecture_root,
            ScanPolicy(excluded_patterns=config.excluded_patterns),
            cache,
        )
        self.cache_diagnostics.record(code_map.outcomes)
        reports = application.analyze_cached_with_diagnostics(code_map.value, config, cache)
        self.cache_diagnostics.record(reports.outcomes)
        formats = tuple(item for item in application.implementation_manifest_formats() if item.id == "canonical-json")
        if len(formats) != 1:
            raise ProjectsError("Modwire must provide exactly one canonical implementation-manifest format.")
        document = application.implementation_manifest(code_map.value.code_map, formats[0])
        return ArchitectureObservation(
            reports=tuple(cast(dict[str, JsonValue], report.to_dict(mode="json")) for report in reports.value),
            implementation_document=cast(dict[str, JsonValue], document.model_dump(mode="json")),
        )

    def verify_source_identity(self, source: ArchitectureSource, expected_digest: str) -> None:
        application = ModwireApplication.create()
        config = self.build_configuration(application, source.boundaries_yaml, source.shape_yaml)
        identity = application.source_manifest_identity(
            source.language,
            source.architecture_root,
            ScanPolicy(excluded_patterns=config.excluded_patterns),
        )
        if identity.digest != expected_digest:
            raise ProjectsError("Project source changed during health evaluation.")

    def build_configuration(
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

    def cache_options(self, workspace_id: str) -> CacheOptions:
        return CacheOptions(
            directory=settings.MODWIRE_CACHE_DIRECTORY,
            namespace=workspace_id,
            max_bytes=settings.MODWIRE_CACHE_MAX_BYTES,
        )
