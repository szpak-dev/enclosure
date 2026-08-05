from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from pgvector.django import CosineDistance
from wireup import injectable

from ....core.models import DjangoRepository
from ...models import Record, Resource


@injectable
@dataclass
class RecordRepository(DjangoRepository):
    model: type[Record] = field(default=Record, init=False)

    def get(self, id: str) -> Record:
        return self.find_all().get(pk=id)

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
        return self.model.objects.select_related("category").prefetch_related("tags", "resources")

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
        self.get(id).delete()

    def search(self, embedding: list[float], limit: int) -> list[Record]:
        return list(
            self.find_all()
            .exclude(embedding__isnull=True)
            .order_by(CosineDistance("embedding", embedding))[:limit]
        )

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
