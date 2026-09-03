from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import QuerySet
from wireup import injectable

from ... import models


@injectable
@dataclass
class GuidanceScopeRepository:
    model: type[models.GuidanceScope] = field(default=models.GuidanceScope, init=False)

    def find(self, project_id: str) -> QuerySet[models.GuidanceScope]:
        return self.model.objects.filter(project_id=project_id).order_by("position", "id")

    @transaction.atomic
    def replace(self, project_id: str, record_ids: tuple[str, ...]) -> QuerySet[models.GuidanceScope]:
        self.model.objects.filter(project_id=project_id).delete()
        self.model.objects.bulk_create(
            self.model(project_id=project_id, record_id=record_id, position=position)
            for position, record_id in enumerate(record_ids, start=1)
        )
        return self.find(project_id)
