from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from django.db import IntegrityError, transaction
from wireup import injectable

from ...core.models import DjangoRepository
from ..errors import ProjectsError
from ..models import Project, ProjectRecord


@injectable
@dataclass
class ProjectRepository(DjangoRepository):
    model: type[Project] = field(default=Project, init=False)

    def get_by_root(self, root: str) -> Project:
        return self.find_all().get(root=root)

    @staticmethod
    def find_record_ids(project_id: str) -> tuple[str, ...]:
        return tuple(
            ProjectRecord.objects.filter(project_id=project_id).values_list("record_id", flat=True)
        )

    def register(self, data: Mapping[str, Any], record_ids: Iterable[str]) -> Project:
        try:
            with transaction.atomic():
                project = self.save(**data)
                self._bind_records(project, record_ids)
                return project
        except IntegrityError as error:
            raise ProjectsError("A project with this root already exists.") from error

    def update(self, id: str, data: Mapping[str, Any], record_ids: Iterable[str]) -> Project:
        try:
            with transaction.atomic():
                project = self.get(id)
                for attribute, value in data.items():
                    setattr(project, attribute, value)
                project.save()
                project.record_bindings.all().delete()
                self._bind_records(project, record_ids)
                return project
        except IntegrityError as error:
            raise ProjectsError("A project with this root already exists.") from error

    @staticmethod
    def _bind_records(project: Project, record_ids: Iterable[str]) -> None:
        ProjectRecord.objects.bulk_create(
            ProjectRecord(project=project, record_id=record_id) for record_id in record_ids
        )
