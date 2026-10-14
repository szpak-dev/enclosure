from dataclasses import dataclass, field

from pydantic import ValidationError
from wireup import injectable

from .. import models
from ..errors import ScaffoldingError
from .model import ScaffoldingCandidate, ScaffoldingValue
from .spec.model import ScaffoldingSpec


@injectable
@dataclass
class ScaffoldingRepository:
    model: type[models.Scaffolding] = field(default=models.Scaffolding, init=False)

    def create(self, candidate: ScaffoldingCandidate) -> ScaffoldingValue:
        scaffolding = self.model.objects.create(
            language_id=candidate.language_id,
            name=candidate.name,
            description=candidate.description,
            spec=candidate.spec.model_dump(mode="json"),
        )
        return self.hydrate(scaffolding)

    def get(self, id: str) -> ScaffoldingValue:
        return self.hydrate(self.model.objects.get(pk=id))

    def find_all(self) -> tuple[ScaffoldingValue, ...]:
        return tuple(self.hydrate(scaffolding) for scaffolding in self.model.objects.order_by("id"))

    def find_page(self, offset: int, limit: int) -> tuple[ScaffoldingValue, ...]:
        scaffoldings = self.model.objects.order_by("id")[offset : offset + limit + 1]
        return tuple(self.hydrate(scaffolding) for scaffolding in scaffoldings)

    def search(self, name: str, language_id: str, limit: int) -> tuple[ScaffoldingValue, ...]:
        scaffoldings = self.model.objects.order_by("id").filter(name__icontains=name)
        if language_id:
            scaffoldings = scaffoldings.filter(language_id=language_id)
        return tuple(self.hydrate(scaffolding) for scaffolding in scaffoldings[:limit])

    def replace(self, id: str, candidate: ScaffoldingCandidate) -> ScaffoldingValue:
        scaffolding = self.model.objects.get(pk=id)
        scaffolding.language_id = candidate.language_id
        scaffolding.name = candidate.name
        scaffolding.description = candidate.description
        scaffolding.spec = candidate.spec.model_dump(mode="json")
        scaffolding.save()
        return self.hydrate(scaffolding)

    def delete(self, id: str) -> None:
        self.model.objects.get(pk=id).delete()

    def hydrate(self, scaffolding: models.Scaffolding) -> ScaffoldingValue:
        try:
            spec = ScaffoldingSpec.model_validate(scaffolding.spec)
        except ValidationError as error:
            raise ScaffoldingError("Persisted scaffolding specification violates its stored contract.") from error
        return ScaffoldingValue(
            id=str(scaffolding.id),
            language_id=scaffolding.language_id,
            name=scaffolding.name,
            description=scaffolding.description,
            spec=spec,
        )
