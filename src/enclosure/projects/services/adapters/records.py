import hashlib
import json
from dataclasses import dataclass

from django.core.exceptions import ObjectDoesNotExist
from wireup import injectable

from enclosure.records.services import RecordsService

from .model import GuidanceRanking, WorkspaceGuidance, WorkspaceGuidanceResolution


@injectable
@dataclass(frozen=True)
class RecordsAdapter:
    records: RecordsService

    def check_records_existence(self, record_ids: tuple[str, ...]) -> None:
        for record_id in record_ids:
            self.records.get_record(record_id)

    def resolve_guidance(
        self,
        record_ids: tuple[str, ...],
    ) -> WorkspaceGuidanceResolution:
        if not record_ids:
            return WorkspaceGuidanceResolution(guidance=(), missing_ids=())

        guidance = []
        missing_ids = []
        for record_id in record_ids:
            try:
                record = self.records.get_record(record_id)
            except ObjectDoesNotExist:
                missing_ids.append(record_id)
                continue
            guidance.append(self._guidance(record))

        return WorkspaceGuidanceResolution(
            guidance=tuple(guidance),
            missing_ids=tuple(missing_ids),
        )

    def rank_guidance(self, record_ids: tuple[str, ...], task: str) -> GuidanceRanking:
        if not record_ids:
            return GuidanceRanking(available=False, ordered_ids=())
        ranked = self.records.search_records(task, len(record_ids), record_ids=record_ids)
        ordered_ids = tuple(record.id for record in ranked)
        return GuidanceRanking(available=bool(ordered_ids), ordered_ids=ordered_ids)

    def _guidance(self, record: object) -> WorkspaceGuidance:
        content = record.content if isinstance(record.content, dict) else {}
        authority = content.get("authority")
        if not isinstance(authority, str) or not authority.strip():
            authority = f"record:{record.id}"
        return WorkspaceGuidance(
            id=record.id,
            title=record.title,
            summary=content.get("summary", record.title),
            authority=authority,
            revision=self._revision(record),
            schema_revision=record.schema_version,
            current_schema_revision=record.category.schema_version,
            applies_when=self._strings(content.get("applies_when")),
            guidance=self._strings(content.get("guidance")),
            checks=self._strings(content.get("checks")),
        )

    def _revision(self, record: object) -> str:
        payload = {
            "id": record.id,
            "title": record.title,
            "content": record.content,
            "category_id": record.category_id,
            "schema_revision": record.schema_version,
            "resources": [
                {
                    "path": resource.path,
                    "language": resource.language,
                    "content": resource.content,
                }
                for _, _, resource in sorted(
                    (resource.path, resource.id, resource) for resource in record.resources.all()
                )
            ],
        }
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()

    def _strings(self, value: object) -> tuple[str, ...]:
        return tuple(item for item in value if isinstance(item, str)) if isinstance(value, list) else ()
