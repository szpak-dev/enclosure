from dataclasses import dataclass, field
from typing import Any

from django.db import IntegrityError, transaction
from wireup import injectable

from ....core.models import DjangoRepository
from ...errors import RecordsError
from ...models import Tag


@injectable
@dataclass
class TagRepository(DjangoRepository):
    model: type[Tag] = field(default=Tag, init=False)

    def save(self, **data: Any) -> Tag:
        try:
            with transaction.atomic():
                return super().save(**data)
        except IntegrityError as error:
            raise RecordsError("A tag with this name already exists.") from error

    def update(self, id: str, **data: Any) -> Tag:
        tag = self.get(id)
        for attribute, value in data.items():
            setattr(tag, attribute, value)
        try:
            with transaction.atomic():
                tag.save()
        except IntegrityError as error:
            raise RecordsError("A tag with this name already exists.") from error
        return tag

    def delete(self, id: str) -> None:
        self.get(id).delete()

    def is_in_use(self, id: str) -> bool:
        return self.find_all().filter(pk=id, records__isnull=False).exists()
