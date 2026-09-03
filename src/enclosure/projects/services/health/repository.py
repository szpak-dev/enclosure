from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import QuerySet
from wireup import injectable

from ... import models
from .model import GuidanceRelationshipInput


@injectable
@dataclass
class GuidanceRelationshipRepository:
    model: type[models.GuidanceRelationship] = field(default=models.GuidanceRelationship, init=False)

    def find(self, project_id: str) -> QuerySet[models.GuidanceRelationship]:
        return self.model.objects.filter(project_id=project_id).order_by("id")

    @transaction.atomic
    def replace(
        self,
        project_id: str,
        relationships: tuple[GuidanceRelationshipInput, ...],
    ) -> QuerySet[models.GuidanceRelationship]:
        self.model.objects.filter(project_id=project_id).delete()
        self.model.objects.bulk_create(
            self.model(
                project_id=project_id,
                source_record_id=relationship.source_record_id,
                target_record_id=relationship.target_record_id,
                kind=relationship.kind.value,
            )
            for relationship in relationships
        )
        return self.find(project_id)
