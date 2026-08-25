from dataclasses import dataclass, field

from django.db.models import QuerySet
from wireup import injectable

from ...core.models import DjangoRepository
from ..models import Scaffolding


@injectable
@dataclass
class ScaffoldingRepository(DjangoRepository):
    model: type[Scaffolding] = field(default=Scaffolding, init=False)

    def search(self, name: str, language_id: str) -> QuerySet[Scaffolding]:
        scaffoldings = self.find_all().filter(name__icontains=name)
        return scaffoldings.filter(language_id=language_id) if language_id else scaffoldings

    def update(self, id: str, **data) -> Scaffolding:
        scaffolding = self.get(id)
        for attribute, value in data.items():
            setattr(scaffolding, attribute, value)
        scaffolding.save()
        return scaffolding

    def delete(self, id: str) -> None:
        self.get(id).delete()
