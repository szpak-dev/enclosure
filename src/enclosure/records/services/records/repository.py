import math
from collections.abc import Iterable
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import QuerySet
from django.db.models.deletion import ProtectedError
from pgvector.django import CosineDistance
from wireup import injectable

from ....core.models import DjangoRepository
from ...errors import RecordsError
from ...models import Record, Resource
from .model import Embedding, RecordCandidate, RecordResourceCandidate


@injectable
@dataclass
class RecordRepository(DjangoRepository):
    model: type[Record] = field(default=Record, init=False)

    def get(self, id: str) -> Record:
        return self.details().get(pk=id)

    def get_resource(self, record_id: str, path: str) -> Resource:
        return Resource.objects.get(record_id=record_id, path=path)

    def get_for_update(self, id: str) -> Record:
        return self.details().select_for_update().get(pk=id)

    def find(
        self,
        category_id: str | None = None,
        tag_ids: Iterable[str] | None = None,
    ) -> QuerySet[Record]:
        records = self.summaries()
        if category_id is not None:
            records = records.filter(category_id=category_id)
        for tag_id in tag_ids or ():
            records = records.filter(tags__id=tag_id)
        return records.distinct()

    def find_all(self, offset: int, limit: int) -> QuerySet[Record]:
        return self.summaries().order_by("id")[offset : offset + limit + 1]

    def summaries(self) -> QuerySet[Record]:
        return self.model.objects.select_related("category").prefetch_related("tags")

    def details(self) -> QuerySet[Record]:
        return self.summaries().prefetch_related("resources")

    @transaction.atomic
    def create(self, candidate: RecordCandidate) -> Record:
        record = self.model.objects.create(
            title=candidate.title,
            content=candidate.content,
            category_id=candidate.category_id,
            schema_version=candidate.schema_version,
            embedding=candidate.embedding.vector(),
        )
        record.tags.set(candidate.tag_ids)
        self._sync_resources(record, candidate.resources)
        return self.get(record.id)

    @transaction.atomic
    def replace(self, id: str, candidate: RecordCandidate) -> Record:
        record = self.get_for_update(id)
        record.title = candidate.title
        record.content = candidate.content
        record.category_id = candidate.category_id
        record.schema_version = candidate.schema_version
        record.embedding = candidate.embedding.vector()
        record.save()
        record.tags.set(candidate.tag_ids)
        self._sync_resources(record, candidate.resources)
        return self.get(record.id)

    @transaction.atomic
    def delete(self, id: str) -> None:
        try:
            with transaction.atomic():
                self.get(id).delete()
        except ProtectedError as error:
            raise RecordsError("A record published in an operating contract cannot be deleted.") from error

    def search(
        self,
        embedding: Embedding,
        limit: int,
        record_ids: tuple[str, ...] | None = None,
    ) -> list[Record]:
        vector = embedding.vector()
        if vector is None:
            return []
        records = self.summaries()
        if record_ids is not None:
            records = records.filter(id__in=record_ids)

        distances: dict[str, float] = {}
        for record_id, distance in (
            records.exclude(embedding__isnull=True)
            .annotate(distance=CosineDistance("embedding", vector))
            .values_list("id", "distance")
        ):
            if distance is not None and math.isfinite(distance):
                distances[record_id] = distance

        resources = Resource.objects.exclude(embedding__isnull=True)
        if record_ids is not None:
            resources = resources.filter(record_id__in=record_ids)
        for record_id, distance in resources.annotate(distance=CosineDistance("embedding", vector)).values_list(
            "record_id", "distance"
        ):
            if distance is None or not math.isfinite(distance):
                continue
            distances[record_id] = min(distance, distances.get(record_id, distance))

        ordered_ids = tuple(
            record_id
            for _, record_id in sorted((distance, record_id) for record_id, distance in distances.items())[:limit]
        )
        records_by_id = {record.id: record for record in records.filter(id__in=ordered_ids)}
        return [records_by_id[record_id] for record_id in ordered_ids]

    def _sync_resources(
        self,
        record: Record,
        resources: tuple[RecordResourceCandidate, ...],
    ) -> None:
        existing_resources = {resource.path: resource for resource in record.resources.all()}
        resource_paths = set()

        for candidate in resources:
            resource_paths.add(candidate.path)
            resource = existing_resources.pop(candidate.path, None)
            if resource is None:
                Resource.objects.create(
                    record=record,
                    path=candidate.path,
                    language=candidate.language,
                    content=candidate.content,
                    embedding=candidate.embedding.vector(),
                )
                continue

            resource.language = candidate.language
            resource.content = candidate.content
            resource.embedding = candidate.embedding.vector()
            resource.save()

        record.resources.exclude(path__in=resource_paths).delete()
