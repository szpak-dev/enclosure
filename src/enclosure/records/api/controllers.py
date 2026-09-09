from typing import Annotated

from modwire_hex.django import DjangoRequest
from ninja import Path, Query, Status
from ninja_extra import ControllerBase, api_controller, http_get, route
from sirenity import siren_pagination

from ..services import RecordsService
from . import schemas


@api_controller("/records/tags", tags=["Record tags"])
class TagsController(ControllerBase):
    @route.post(
        "",
        response={201: schemas.Tag},
        operation_id="create_record_tag",
        summary="Create a record tag",
        description="Create a tag for classifying records.",
    )
    def create(self, request, body: schemas.WriteTag):
        tag = DjangoRequest.resolve(request, RecordsService).create_tag(body.model_dump(mode="json"))
        return Status(201, tag)

    @siren_pagination(
        http_get,
        response=schemas.TagPage,
        operation_id="find_record_tags",
        continuation={"offset": "next_offset", "limit": "limit"},
        summary="List record tags",
        description="Return one bounded page of tags available for classifying records.",
    )
    def find_all(self, request, query: Query[schemas.FindPage]):
        return DjangoRequest.resolve(request, RecordsService).find_tag_page(query.offset, query.limit)

    @route.get(
        "/{tag_id}",
        response=schemas.Tag,
        operation_id="get_record_tag",
        summary="Get a record tag",
        description="Return a tag used to classify records.",
    )
    def get(self, request, tag_id: Annotated[str, Path(description="Record tag identifier.")]):
        return DjangoRequest.resolve(request, RecordsService).get_tag(tag_id)

    @route.put(
        "/{tag_id}",
        response=schemas.Tag,
        operation_id="update_record_tag",
        summary="Update a record tag",
        description="Replace a record tag's name.",
    )
    def update(
        self,
        request,
        tag_id: Annotated[str, Path(description="Record tag identifier.")],
        body: schemas.WriteTag,
    ):
        return DjangoRequest.resolve(request, RecordsService).update_tag(tag_id, body.model_dump(mode="json"))

    @route.delete(
        "/{tag_id}",
        response={204: None},
        operation_id="delete_record_tag",
        summary="Delete a record tag",
        description="Delete an unused record tag.",
    )
    def delete(self, request, tag_id: Annotated[str, Path(description="Record tag identifier.")]):
        DjangoRequest.resolve(request, RecordsService).delete_tag(tag_id)
        return Status(204, None)


@api_controller("/records", tags=["Records"])
class RecordsController(ControllerBase):
    @route.post(
        "",
        response={201: schemas.Record},
        operation_id="create_record",
        summary="Create a record",
        description="Store a categorized, tagged record and its source resources.",
    )
    def create(self, request, body: schemas.WriteRecord):
        record = DjangoRequest.resolve(request, RecordsService).create_record_detail(body.model_dump(mode="json"))
        return Status(201, record)

    @siren_pagination(
        http_get,
        response=schemas.RecordPage,
        operation_id="find_records",
        continuation={"offset": "next_offset", "limit": "limit"},
        summary="List records",
        description="Return one bounded page of compact record summaries.",
    )
    def find_all(self, request, query: Query[schemas.FindPage]):
        return DjangoRequest.resolve(request, RecordsService).find_record_page(query.offset, query.limit)

    @route.post(
        "/search-results",
        response=list[schemas.RecordSummary],
        operation_id="search_records",
        summary="Search records",
        description="Find compact record summaries by semantic similarity to a natural-language query.",
    )
    def search(self, request, body: schemas.SearchRecords):
        return DjangoRequest.resolve(request, RecordsService).search_records(body.query, body.limit)

    @route.post(
        "/categories",
        response={201: schemas.Category},
        operation_id="create_record_category",
        summary="Create a record category",
        description="Create a category whose JSON Schema validates record content.",
    )
    def create_category(self, request, body: schemas.CreateCategory):
        category = DjangoRequest.resolve(request, RecordsService).create_category_detail(body.model_dump(mode="json"))
        return Status(201, category)

    @siren_pagination(
        http_get,
        "/categories",
        response=schemas.CategoryPage,
        operation_id="find_record_categories",
        continuation={"offset": "next_offset", "limit": "limit"},
        summary="List record categories",
        description="Return one bounded page of compact record category references.",
    )
    def find_all_categories(self, request, query: Query[schemas.FindPage]):
        return DjangoRequest.resolve(request, RecordsService).find_category_page(query.offset, query.limit)

    @route.get(
        "/categories/{category_id}",
        response=schemas.Category,
        operation_id="get_record_category",
        summary="Get a record category",
        description="Return a record category and its content schema.",
    )
    def get_category(
        self,
        request,
        category_id: Annotated[str, Path(description="Record category identifier.")],
    ):
        return DjangoRequest.resolve(request, RecordsService).get_category_detail(category_id)

    @route.put(
        "/categories/{category_id}",
        response=schemas.Category,
        operation_id="update_record_category",
        summary="Update a record category",
        description="Replace a record category's title.",
    )
    def update_category(
        self,
        request,
        category_id: Annotated[str, Path(description="Record category identifier.")],
        body: schemas.UpdateCategory,
    ):
        return DjangoRequest.resolve(request, RecordsService).update_category_detail(
            category_id,
            body.model_dump(mode="json"),
        )

    @route.put(
        "/categories/{category_id}/content-schema",
        response=schemas.CategorySchemaRevision,
        operation_id="update_record_category_content_schema",
        summary="Update a record category content schema",
        description="Replace an unreferenced schema or publish its next immutable version.",
    )
    def update_category_content_schema(
        self,
        request,
        category_id: Annotated[str, Path(description="Record category identifier.")],
        body: schemas.UpdateCategoryContentSchema,
    ):
        return DjangoRequest.resolve(request, RecordsService).update_category_content_schema_receipt(
            category_id,
            body.content_schema,
        )

    @route.get(
        "/categories/{category_id}/content-schema",
        response=schemas.RecordCategoryContentSchema,
        operation_id="read_record_category_content_schema",
        summary="Read a record category content schema",
        description="Read one bounded page from a revision-pinned category content schema.",
    )
    def read_category_content_schema(
        self,
        request,
        category_id: Annotated[str, Path(description="Record category identifier.")],
        query: Query[schemas.ReadRecordCategoryContentSchema],
    ):
        return DjangoRequest.resolve(request, RecordsService).read_record_category_content_schema(
            category_id,
            query.schema_version,
            query.expected_revision,
            query.offset,
            query.limit,
        )

    @route.delete(
        "/categories/{category_id}",
        response={204: None},
        operation_id="delete_record_category",
        summary="Delete a record category",
        description="Delete an unused record category.",
    )
    def delete_category(
        self,
        request,
        category_id: Annotated[str, Path(description="Record category identifier.")],
    ):
        DjangoRequest.resolve(request, RecordsService).delete_category(category_id)
        return Status(204, None)

    @route.get(
        "/{record_id}",
        response=schemas.Record,
        operation_id="get_record",
        summary="Get a record",
        description="Return a record with its category, tags, content, and source resources.",
    )
    def get(self, request, record_id: Annotated[str, Path(description="Record identifier.")]):
        return DjangoRequest.resolve(request, RecordsService).get_record_detail(record_id)

    @route.get(
        "/{record_id}/resources/content",
        response=schemas.RecordResourceContent,
        operation_id="read_record_resource",
        summary="Read a record resource",
        description="Read one bounded page from an exact revision-pinned record resource path.",
    )
    def read_resource(
        self,
        request,
        record_id: Annotated[str, Path(description="Record identifier.")],
        query: Query[schemas.ReadRecordResource],
    ):
        return DjangoRequest.resolve(request, RecordsService).read_record_resource(
            record_id,
            query.path,
            query.expected_revision,
            query.offset,
            query.limit,
        )

    @route.put(
        "/{record_id}",
        response=schemas.Record,
        operation_id="update_record",
        summary="Update a record",
        description="Replace a record's category, tags, content, and source resources.",
    )
    def update(
        self,
        request,
        record_id: Annotated[str, Path(description="Record identifier.")],
        body: schemas.WriteRecord,
    ):
        return DjangoRequest.resolve(request, RecordsService).update_record_detail(
            record_id,
            body.model_dump(mode="json"),
        )

    @route.delete(
        "/{record_id}",
        response={204: None},
        operation_id="delete_record",
        summary="Delete a record",
        description="Permanently delete a record and its source resources.",
    )
    def delete(self, request, record_id: Annotated[str, Path(description="Record identifier.")]):
        DjangoRequest.resolve(request, RecordsService).delete_record(record_id)
        return Status(204, None)
