from dataclasses import dataclass

from wireup import injectable

from enclosure.records.services import RecordsService


@injectable
@dataclass(frozen=True)
class RecordsAdapter:
    records: RecordsService

    def check_records_existence(self, record_ids: list[str]) -> None:
        for record_id in record_ids:
            self.records.get_record(record_id)

    def find_guidance(
        self,
        record_ids: tuple[str, ...],
        task: str,
        limit: int = 3,
    ) -> tuple[dict[str, object], ...]:
        if not record_ids:
            return ()
        records = self.records.search_records(
            task,
            min(limit, len(record_ids)),
            record_ids=record_ids,
        )
        guidance = []
        for record in records:
            content = record.content if isinstance(record.content, dict) else {}
            guidance.append(
                {
                    "id": record.id,
                    "title": record.title,
                    "summary": content.get("summary", record.title),
                    "applies_when": self._strings(content.get("applies_when")),
                    "guidance": self._strings(content.get("guidance")),
                    "checks": self._strings(content.get("checks")),
                }
            )
        return tuple(guidance)

    @staticmethod
    def _strings(value: object) -> list[str]:
        return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
