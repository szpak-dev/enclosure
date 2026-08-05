from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from django.db.models import QuerySet
from wireup import injectable

from ...errors import RecordsError
from ...models import Record
from .embeddings import RecordsEmbeddingsService
from .repository import RecordRepository
from .resource_validator import ResourceValidator


@injectable
@dataclass(frozen=True)
class RecordService:
    repository: RecordRepository
    resources: ResourceValidator
    embeddings: RecordsEmbeddingsService

    def create(self, data: dict) -> Record:
        return self._save(data)

    def get(self, id: str) -> Record:
        return self.repository.get(id)

    def find_all(self) -> QuerySet[Record]:
        return self.repository.find_all()

    def search(self, query: str, limit: int = 10) -> list[Record]:
        return self.repository.search(self.embeddings.embed_query(query), limit)

    def update(self, id: str, data: dict) -> Record:
        return self._save({**self._snapshot(self.get(id)), **data, "id": id})

    def delete(self, id: str) -> None:
        self.repository.delete(id)

    def _save(self, data: Mapping[str, Any]) -> Record:
        record_data, tag_ids, resources = self._prepare(data)
        for resource in resources:
            self.resources.validate(
                resource["language"],
                resource["path"],
                resource["content"],
            )
        self._assign_embeddings(record_data, resources)
        return self.repository.save(record_data, tag_ids, resources)

    @staticmethod
    def _snapshot(record: Record) -> dict:
        return {
            "title": record.title,
            "content": record.content,
            "category_id": record.category_id,
            "schema_version": record.schema_version,
            "tag_ids": [tag.id for tag in record.tags.all()],
            "resources": [
                {
                    "path": resource.path,
                    "language": resource.language,
                    "content": resource.content,
                }
                for resource in record.resources.all()
            ],
        }

    @staticmethod
    def _prepare(data: Mapping[str, Any]) -> tuple[dict, list[str], list[dict]]:
        record_data = {
            key: data[key]
            for key in ("id", "title", "content", "category_id", "schema_version")
            if key in data
        }
        tag_ids = list(data["tag_ids"])
        resources = [dict(resource) for resource in data.get("resources", ())]
        resource_paths = [resource["path"] for resource in resources]
        if len(resource_paths) != len(set(resource_paths)):
            raise RecordsError("A record cannot contain multiple resources with the same path.")
        return record_data, tag_ids, resources

    def _assign_embeddings(self, record_data: dict, resources: list[dict]) -> None:
        record_data["embedding"] = self.embeddings.embed_record(record_data["title"], record_data["content"])
        for resource in resources:
            resource["embedding"] = self.embeddings.embed_resource(
                resource["path"],
                resource["language"],
                resource["content"],
            )
