import json
from dataclasses import dataclass
from hashlib import sha256
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
from ..model import (
    ArchitectureCodeMapObservation,
    ArchitectureObservation,
    ArchitectureReportObservation,
    ArchitectureSource,
)


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
        observation = self.code_map(source)
        return self.observe_reports(source, observation).reports

    def code_map(self, source: ArchitectureSource) -> ArchitectureCodeMapObservation:
        application = ModwireApplication.create()
        config = self.build_configuration(application, source.boundaries_yaml, source.shape_yaml)
        cache = self.cache_options(source.workspace_id)
        result = application.generate_queryable_map_cached_with_diagnostics(
            source.language,
            source.architecture_root,
            ScanPolicy(excluded_patterns=config.excluded_patterns),
            cache,
        )
        self.cache_diagnostics.record(result.outcomes)
        return ArchitectureCodeMapObservation(
            code_map=result.value,
            source_digest=result.value.code_map.extraction.manifest.digest,
        )

    def observe_reports(
        self,
        source: ArchitectureSource,
        observation: ArchitectureCodeMapObservation,
    ) -> ArchitectureReportObservation:
        application = ModwireApplication.create()
        config = self.build_configuration(application, source.boundaries_yaml, source.shape_yaml)
        cache = self.cache_options(source.workspace_id)
        reports = application.analyze_cached_with_diagnostics(observation.code_map, config, cache)
        self.cache_diagnostics.record(reports.outcomes)
        return ArchitectureReportObservation(
            reports=tuple(cast(dict[str, JsonValue], report.to_dict(mode="json")) for report in reports.value),
            source_digest=observation.source_digest,
        )

    def observe(self, observation: ArchitectureCodeMapObservation) -> ArchitectureObservation:
        application = ModwireApplication.create()
        formats = tuple(item for item in application.implementation_manifest_formats() if item.id == "canonical-json")
        if len(formats) != 1:
            raise ProjectsError("Modwire must provide exactly one canonical implementation-manifest format.")
        document = application.implementation_manifest(observation.code_map.code_map, formats[0])
        implementation_document = cast(dict[str, JsonValue], document.model_dump(mode="json"))
        canonical_document = json.dumps(
            implementation_document,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return ArchitectureObservation(
            implementation_document=implementation_document,
            source_digest=observation.source_digest,
            document_digest=sha256(canonical_document.encode("utf-8")).hexdigest(),
        )

    def source_identity(self, source: ArchitectureSource) -> str:
        application = ModwireApplication.create()
        config = self.build_configuration(application, source.boundaries_yaml, source.shape_yaml)
        identity = application.source_manifest_identity(
            source.language,
            source.architecture_root,
            ScanPolicy(excluded_patterns=config.excluded_patterns),
        )
        return identity.digest

    def verify_source_identity(self, source: ArchitectureSource, expected_digest: str) -> None:
        if self.source_identity(source) != expected_digest:
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
