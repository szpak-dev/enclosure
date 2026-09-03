import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from django.db.models.deletion import ProtectedError
from pgvector.django import CosineDistance
from wireup import injectable

from ....core.models import DjangoRepository
from ...errors import RecordsError
from ...models import Record, Resource


@injectable
@dataclass
class RecordRepository(DjangoRepository):
    model: type[Record] = field(default=Record, init=False)

    def get(self, id: str) -> Record:
        return self.details().get(pk=id)

    def find(
        self,
        category_id: str | None = None,
        tag_ids: Iterable[str] | None = None,
    ) -> QuerySet[Record]:
        records = self.find_all()
        if category_id is not None:
            records = records.filter(category_id=category_id)
        for tag_id in tag_ids or ():
            records = records.filter(tags__id=tag_id)
        return records.distinct()

    def find_all(self) -> QuerySet[Record]:
        return self.summaries()

    def summaries(self) -> QuerySet[Record]:
        return self.model.objects.select_related("category").prefetch_related("tags")

    def details(self) -> QuerySet[Record]:
        return self.summaries().prefetch_related("resources")

    @transaction.atomic
    def save(
        self,
        record_data: Mapping[str, Any],
        tag_ids: Iterable[str],
        resources: Iterable[Mapping[str, Any]],
    ) -> Record:
        data = dict(record_data)
        record_id = data.pop("id", None)
        if record_id is None:
            record = self.model(**data)
        else:
            record = self.get(record_id)
            for attribute, value in data.items():
                setattr(record, attribute, value)

        record.save()
        record.tags.set(tag_ids)
        self._sync_resources(record, resources)
        return self.get(record.id)

    @transaction.atomic
    def delete(self, id: str) -> None:
        try:
            self.get(id).delete()
        except ProtectedError as error:
            raise RecordsError("A record published in an operating contract cannot be deleted.") from error

    def search(
        self,
        embedding: list[float],
        limit: int,
        record_ids: tuple[str, ...] | None = None,
    ) -> list[Record]:
        if embedding is None:
            return []
        records = self.summaries()
        if record_ids is not None:
            records = records.filter(id__in=record_ids)

        distances: dict[str, float] = {}
        for record_id, distance in (
            records.exclude(embedding__isnull=True)
            .annotate(distance=CosineDistance("embedding", embedding))
            .values_list("id", "distance")
        ):
            if distance is not None and math.isfinite(distance):
                distances[record_id] = distance

        resources = Resource.objects.exclude(embedding__isnull=True)
        if record_ids is not None:
            resources = resources.filter(record_id__in=record_ids)
        for record_id, distance in resources.annotate(distance=CosineDistance("embedding", embedding)).values_list(
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

    def _sync_resources(self, record: Record, resources: Iterable[Mapping[str, Any]]) -> None:
        existing_resources = {resource.path: resource for resource in record.resources.all()}
        resource_paths = set()

        for resource_data in resources:
            data = dict(resource_data)
            path = data["path"]
            resource_paths.add(path)
            resource = existing_resources.pop(path, None)
            if resource is None:
                Resource.objects.create(record=record, **data)
                continue

            for attribute, value in data.items():
                setattr(resource, attribute, value)
            resource.save()

        record.resources.exclude(path__in=resource_paths).delete()
