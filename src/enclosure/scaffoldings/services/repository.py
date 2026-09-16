from dataclasses import dataclass, field

from django.db.models import QuerySet
from wireup import injectable

from ...core.models import DjangoRepository
from ..models import Scaffolding


@injectable
@dataclass
class ScaffoldingRepository(DjangoRepository):
    model: type[Scaffolding] = field(default=Scaffolding, init=False)

    def find_all(self) -> QuerySet[Scaffolding]:
        return super().find_all().order_by("id")

    def find_page(self, offset: int, limit: int) -> tuple[Scaffolding, ...]:
        return tuple(self.find_all()[offset : offset + limit + 1])

    def search(self, name: str, language_id: str, limit: int) -> QuerySet[Scaffolding]:
        scaffoldings = self.find_all().filter(name__icontains=name)
        matches = scaffoldings.filter(language_id=language_id) if language_id else scaffoldings
        return matches[:limit]

    def update(self, id: str, **data) -> Scaffolding:
        scaffolding = self.get(id)
        for attribute, value in data.items():
            setattr(scaffolding, attribute, value)
        scaffolding.save()
        return scaffolding

    def delete(self, id: str) -> None:
        self.get(id).delete()
