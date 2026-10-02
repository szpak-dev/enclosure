from dataclasses import dataclass

from django.db.models import QuerySet
from wireup import injectable

from ...models import Record, Resource
from .embeddings import RecordsEmbeddingsService
from .model import RecordCandidate, RecordInput, RecordResourceCandidate
from .repository import RecordRepository
from .resource_validator import ResourceValidator


@injectable
@dataclass(frozen=True)
class RecordService:
    repository: RecordRepository
    resources: ResourceValidator
    embeddings: RecordsEmbeddingsService

    def create(self, data: RecordInput, schema_version: int) -> Record:
        return self.repository.create(self._candidate(data, schema_version))

    def get(self, id: str) -> Record:
        return self.repository.get(id)

    def get_resource(self, record_id: str, path: str) -> Resource:
        return self.repository.get_resource(record_id, path)

    def find_all(self, offset: int, limit: int) -> QuerySet[Record]:
        return self.repository.find_all(offset, limit)

    def search(
        self,
        query: str,
        limit: int = 10,
        record_ids: tuple[str, ...] | None = None,
    ) -> list[Record]:
        return self.repository.search(self.embeddings.embed_query(query), limit, record_ids)

    def schema_version(self, id: str, category_id: str, current_schema_version: int) -> int:
        record = self.repository.get_for_update(id)
        if record.category_id == category_id:
            return record.schema_version
        return current_schema_version

    def update(self, id: str, data: RecordInput, schema_version: int) -> Record:
        return self.repository.replace(id, self._candidate(data, schema_version))

    def delete(self, id: str) -> None:
        self.repository.delete(id)

    def _candidate(self, data: RecordInput, schema_version: int) -> RecordCandidate:
        for resource in data.resources:
            self.resources.validate(
                resource.language,
                resource.path,
                resource.content,
            )
        return RecordCandidate(
            title=data.title,
            content=data.content,
            category_id=data.category_id,
            schema_version=schema_version,
            tag_ids=data.tag_ids,
            resources=tuple(
                RecordResourceCandidate(
                    path=resource.path,
                    language=resource.language,
                    content=resource.content,
                    embedding=self.embeddings.embed_resource(
                        resource.path,
                        resource.language,
                        resource.content,
                    ),
                )
                for resource in data.resources
            ),
            embedding=self.embeddings.embed_record(data.title, data.content),
        )
