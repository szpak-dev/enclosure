import json
from dataclasses import dataclass
from hashlib import sha256
from typing import ClassVar, cast

from pydantic import JsonValue
from wireup import injectable

from ....errors import ProjectsError
from ..model import (
    ArchitectureGroupInput,
    ArchitectureMapReportInput,
    ArchitectureReportMetadata,
    CallableInput,
    ClusterInput,
    ExportInput,
    HotspotInput,
    InsightPage,
    InsightReportInput,
    InsightReportSet,
    InsightSection,
)


@injectable
@dataclass(frozen=True)
class InsightPagingService:
    MAX_PAGE_ITEMS: ClassVar[int] = 25

    def revision(self, reports: tuple[dict[str, JsonValue], ...]) -> str:
        canonical = json.dumps(
            reports,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return sha256(canonical).hexdigest()

    def page(
        self,
        report: InsightReportSet,
        path: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> InsightPage:
        if report.revision != expected_revision:
            raise ProjectsError("Project insights changed; read them again before requesting a page.")
        if limit < 1 or limit > self.MAX_PAGE_ITEMS:
            raise ProjectsError(f"Project insight page limit must be between 1 and {self.MAX_PAGE_ITEMS}.")
        collections = self._collections(report)
        if path not in collections:
            raise ProjectsError("Project insight path must identify a collection.")
        collection = collections[path]
        if offset < 0 or offset > len(collection):
            raise ProjectsError("Project insight page offset is outside the collection.")
        next_offset = min(offset + limit, len(collection))
        items = collection[offset:next_offset]
        return InsightPage(
            project_id=report.project_id,
            workspace_id=report.workspace_id,
            revision=report.revision,
            path=path,
            offset=offset,
            limit=limit,
            total=len(collection),
            items=items,
            has_more=next_offset < len(collection),
            next_offset=next_offset,
        )

    def sections(self, report: InsightReportSet) -> tuple[InsightSection, ...]:
        return tuple(
            InsightSection(path=path, total=len(items)) for path, items in self._collections(report).items() if items
        )

    def escape(self, segment: str) -> str:
        return segment.replace("~", "~0").replace("/", "~1")

    def _collections(self, report: InsightReportSet) -> dict[str, tuple[JsonValue, ...]]:
        collections: dict[str, tuple[JsonValue, ...]] = {}
        for item in report.reports:
            metadata = cast(ArchitectureReportMetadata, item["metadata"])
            report_id = metadata["id"]
            root = f"/{self.escape(report_id)}"
            if any(path.startswith(f"{root}/") for path in collections):
                raise ProjectsError("Project insight reports require unique stable identifiers.")
            if report_id == "architecture.map":
                collections.update(self._map_collections(cast(ArchitectureMapReportInput, item), root))
            elif report_id == "architecture.insights":
                collections.update(self._insight_collections(cast(InsightReportInput, item), root))
            else:
                raise ProjectsError(f"Unsupported project insight report {report_id!r}.")
        return collections

    def _map_collections(
        self,
        report: ArchitectureMapReportInput,
        root: str,
    ) -> dict[str, tuple[JsonValue, ...]]:
        modules_path = f"{root}/modules"
        layers_path = f"{root}/layers"
        metadata_path = f"{root}/metadata/children"
        return {
            modules_path: tuple(
                self._architecture_group(group, self._join(modules_path, str(index)))
                for index, group in enumerate(report["modules"])
            ),
            layers_path: tuple(
                self._architecture_group(group, self._join(layers_path, str(index)))
                for index, group in enumerate(report["layers"])
            ),
            f"{root}/unknown_files": tuple(report["unknown_files"]),
            metadata_path: tuple(
                self._metadata(metadata, self._join(metadata_path, str(index)))
                for index, metadata in enumerate(report["metadata"]["children"])
            ),
        }

    def _insight_collections(
        self,
        report: InsightReportInput,
        root: str,
    ) -> dict[str, tuple[JsonValue, ...]]:
        cluster_path = f"{root}/clusters/clusters"
        hotspot_path = f"{root}/hotspots/hotspots"
        callable_path = f"{root}/callables/entries"
        export_path = f"{root}/exports/unused_exports"
        metadata_path = f"{root}/metadata/children"
        return {
            cluster_path: tuple(
                self._cluster(cluster, self._join(cluster_path, str(index)))
                for index, cluster in enumerate(report["clusters"]["clusters"])
            ),
            hotspot_path: tuple(self._hotspot(hotspot) for hotspot in report["hotspots"]["hotspots"]),
            f"{root}/coherence/roots": tuple(report["coherence"]["roots"]),
            f"{root}/coherence/leaves": tuple(report["coherence"]["leaves"]),
            f"{root}/coherence/isolated": tuple(report["coherence"]["isolated"]),
            f"{root}/coherence/external_dependencies": tuple(report["coherence"]["external_dependencies"]),
            callable_path: tuple(
                self._callable(entry, self._join(callable_path, str(index)))
                for index, entry in enumerate(report["callables"]["entries"])
            ),
            export_path: tuple(self._export(entry) for entry in report["exports"]["unused_exports"]),
            metadata_path: tuple(
                self._metadata(metadata, self._join(metadata_path, str(index)))
                for index, metadata in enumerate(report["metadata"]["children"])
            ),
        }

    def _architecture_group(self, group: ArchitectureGroupInput, path: str) -> JsonValue:
        return {
            "name": group["name"],
            "source_ids": {"path": self._join(path, "source_ids"), "total": len(group["source_ids"])},
        }

    def _cluster(self, cluster: ClusterInput, path: str) -> JsonValue:
        return {
            "name": cluster["name"],
            "files": {"path": self._join(path, "files"), "total": len(cluster["files"])},
            "incoming_count": cluster["incoming_count"],
            "outgoing_count": cluster["outgoing_count"],
            "pressure_score": cluster["pressure_score"],
            "top_files": {"path": self._join(path, "top_files"), "total": len(cluster["top_files"])},
        }

    def _hotspot(self, hotspot: HotspotInput) -> JsonValue:
        return {
            "source_id": hotspot["source_id"],
            "incoming_count": hotspot["incoming_count"],
            "outgoing_count": hotspot["outgoing_count"],
            "pressure_score": hotspot["pressure_score"],
        }

    def _callable(self, entry: CallableInput, path: str) -> JsonValue:
        return {
            "source_callable": entry["source_callable"],
            "calls": {"path": self._join(path, "calls"), "total": len(entry["calls"])},
            "callers": {"path": self._join(path, "callers"), "total": len(entry["callers"])},
        }

    def _export(self, entry: ExportInput) -> JsonValue:
        return {
            "source_id": entry["source_id"],
            "name": entry["name"],
            "kind": entry["kind"],
            "crossing_type": entry["crossing_type"],
            "reason": entry["reason"],
        }

    def _metadata(self, metadata: ArchitectureReportMetadata, path: str) -> JsonValue:
        return {
            "id": metadata["id"],
            "title": metadata["title"],
            "description": metadata["description"],
            "model": metadata["model"],
            "path": metadata["path"],
            "order": metadata["order"],
            "children": {"path": self._join(path, "children"), "total": len(metadata["children"])},
        }

    def _join(self, path: str, segment: str) -> str:
        return f"{path.rstrip('/')}/{segment}"
