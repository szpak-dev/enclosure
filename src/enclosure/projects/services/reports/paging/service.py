import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import ClassVar

from pydantic import JsonValue
from wireup import injectable

from ....errors import ProjectsError
from ..model import InsightPage, InsightReportSet, InsightSection


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
        collection = self._resolve(report, path)
        if offset < 0 or offset > len(collection):
            raise ProjectsError("Project insight page offset is outside the collection.")
        next_offset = min(offset + limit, len(collection))
        items = tuple(
            self._project(item, self._join(path, str(index)))
            for index, item in enumerate(collection[offset:next_offset], start=offset)
        )
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
        sections = []
        for report_id, item in self._reports(report).items():
            sections.extend(self._sections(item, f"/{self.escape(report_id)}"))
        return tuple(sections)

    def escape(self, segment: str) -> str:
        return segment.replace("~", "~0").replace("/", "~1")

    def _resolve(self, report: InsightReportSet, path: str) -> list[JsonValue] | tuple[JsonValue, ...]:
        if not path.startswith("/"):
            raise ProjectsError("Project insight path must be an absolute JSON pointer.")
        current: JsonValue = self._reports(report)
        for segment in self._segments(path):
            if isinstance(current, Mapping):
                if segment not in current:
                    raise ProjectsError("Project insight path does not exist.")
                current = current[segment]
                continue
            if isinstance(current, list | tuple) and segment.isdigit():
                index = int(segment)
                if index >= len(current):
                    raise ProjectsError("Project insight path does not exist.")
                current = current[index]
                continue
            raise ProjectsError("Project insight path does not exist.")
        if not isinstance(current, list | tuple):
            raise ProjectsError("Project insight path must identify a collection.")
        return current

    def _reports(self, report: InsightReportSet) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {}
        for item in report.reports:
            metadata = item.get("metadata")
            report_id = metadata.get("id") if isinstance(metadata, Mapping) else ""
            if not isinstance(report_id, str) or not report_id or report_id in result:
                raise ProjectsError("Project insight reports require unique stable identifiers.")
            result[report_id] = item
        return result

    def _sections(self, value: JsonValue, path: str) -> list[InsightSection]:
        sections = []
        if isinstance(value, Mapping):
            for name, item in value.items():
                child_path = self._join(path, self.escape(str(name)))
                if isinstance(item, list | tuple):
                    if item:
                        sections.append(InsightSection(path=child_path, total=len(item)))
                elif isinstance(item, Mapping):
                    sections.extend(self._sections(item, child_path))
        return sections

    def _project(self, value: JsonValue, path: str) -> JsonValue:
        if isinstance(value, list | tuple):
            return {"path": path, "total": len(value)}
        if isinstance(value, Mapping):
            return {
                str(name): self._project(item, self._join(path, self.escape(str(name)))) for name, item in value.items()
            }
        return value

    def _segments(self, path: str) -> tuple[str, ...]:
        if path == "/":
            return ("",)
        return tuple(segment.replace("~1", "/").replace("~0", "~") for segment in path[1:].split("/"))

    def _join(self, path: str, segment: str) -> str:
        return f"{path.rstrip('/')}/{segment}"
