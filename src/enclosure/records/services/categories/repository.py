from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from wireup import injectable

from ....core.models import DjangoRepository
from ...errors import RecordsError
from ...models import Category, CategorySchemaRevision


@injectable
@dataclass
class CategoryRepository(DjangoRepository):
    model: type[Category] = field(default=Category, init=False)

    @transaction.atomic
    def save(self, title: str, content_schema: dict) -> Category:
        try:
            category = super().save(
                title=title,
                content_schema=content_schema,
                schema_version=1,
            )
            CategorySchemaRevision.objects.create(
                category=category,
                version=category.schema_version,
                content_schema=content_schema,
            )
        except IntegrityError as error:
            raise RecordsError("A category with this title already exists.") from error
        return category

    def update(self, id: str, title: str) -> Category:
        category = self.get(id)
        category.title = title
        try:
            category.save()
        except IntegrityError as error:
            raise RecordsError("A category with this title already exists.") from error
        return category

    @transaction.atomic
    def update_content_schema(self, id: str, content_schema: dict) -> CategorySchemaRevision:
        category = self.model.objects.select_for_update().get(pk=id)
        if category.records.exists():
            category.schema_version += 1
            revision = CategorySchemaRevision.objects.create(
                category=category,
                version=category.schema_version,
                content_schema=content_schema,
            )
        else:
            revision = self.get_revision(id, category.schema_version)
            revision.content_schema = content_schema
            revision.save(update_fields=("content_schema",))

        category.content_schema = content_schema
        category.save(update_fields=("content_schema", "schema_version"))
        return revision

    def get_revision(self, category_id: str, version: int) -> CategorySchemaRevision:
        return CategorySchemaRevision.objects.get(category_id=category_id, version=version)

    def delete(self, id: str) -> None:
        try:
            self.get(id).delete()
        except ProtectedError as error:
            raise RecordsError("A category assigned to records cannot be deleted.") from error
