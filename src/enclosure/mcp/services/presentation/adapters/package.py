from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from operator import attrgetter
from typing import ClassVar

from wireup import injectable

from ..errors import PresentationTemplateNotFound
from ..model import PresentationTemplate
from ..repository import PresentationTemplateRepository


@injectable(as_type=PresentationTemplateRepository)
@dataclass(frozen=True)
class PackagePresentationTemplateRepository(PresentationTemplateRepository):
    package: ClassVar[str] = "enclosure.mcp.services.presentation"
    root: ClassVar[str] = "templates"

    def find(self, operation_id: str) -> PresentationTemplate:
        try:
            for template in self._discover():
                if template.operation_id == operation_id:
                    return template
        except (ModuleNotFoundError, OSError, TypeError) as error:
            raise PresentationTemplateNotFound(operation_id) from error
        raise PresentationTemplateNotFound(operation_id)

    def find_all(self, operation_ids: tuple[str, ...]) -> tuple[PresentationTemplate, ...]:
        try:
            templates = {template.operation_id: template for template in self._discover()}
            published = set(operation_ids)
            if len(published) != len(operation_ids):
                raise ValueError("The MCP catalogue contains duplicate operation identifiers.")
            stale = sorted(templates.keys() - published)
            if stale:
                raise ValueError(f"Presentation templates are not published MCP operations: {', '.join(stale)}.")
            strategies = []
            for operation_id in operation_ids:
                strategies.append(
                    templates[operation_id] if operation_id in templates else self._shared("incomplete", operation_id)
                )
            return tuple(strategies)
        except (ModuleNotFoundError, OSError, TypeError) as error:
            raise PresentationTemplateNotFound("presentation-strategies") from error

    def error(self) -> PresentationTemplate:
        try:
            return self._shared("error", "error")
        except (ModuleNotFoundError, OSError, TypeError) as error:
            raise PresentationTemplateNotFound("error") from error

    def incomplete(self) -> PresentationTemplate:
        try:
            return self._shared("incomplete", "incomplete")
        except (ModuleNotFoundError, OSError, TypeError) as error:
            raise PresentationTemplateNotFound("incomplete") from error

    def _discover(self) -> tuple[PresentationTemplate, ...]:
        discovered: dict[str, dict[str, str]] = {}
        applications: dict[str, str] = {}
        template_root = files(self.package).joinpath(self.root)
        for application in self._entries(template_root):
            if not application.is_dir() or application.name == "shared":
                continue
            for resource in self._entries(application):
                suffix = self._suffix(resource)
                if not suffix:
                    continue
                operation_id = resource.name.removesuffix(suffix)
                if operation_id in applications and applications[operation_id] != application.name:
                    raise ValueError(f"Presentation template '{operation_id}' is declared more than once.")
                applications[operation_id] = application.name
                discovered.setdefault(operation_id, {})[suffix] = f"{application.name}/{resource.name}"

        templates = []
        for operation_id in sorted(discovered):
            pair = discovered[operation_id]
            if ".md.jinja" not in pair or ".json.jinja" not in pair:
                raise ValueError(f"Presentation template '{operation_id}' does not have a complete pair.")
            templates.append(
                PresentationTemplate(
                    operation_id=operation_id,
                    application=applications[operation_id],
                    package=self.package,
                    markdown_path=pair[".md.jinja"],
                    structured_path=pair[".json.jinja"],
                )
            )
        return tuple(templates)

    def _entries(self, directory: Traversable) -> tuple[Traversable, ...]:
        return tuple(sorted(directory.iterdir(), key=attrgetter("name")))

    def _suffix(self, resource: Traversable) -> str:
        if not resource.is_file():
            return ""
        for suffix in (".md.jinja", ".json.jinja"):
            if resource.name.endswith(suffix):
                return suffix
        return ""

    def _shared(self, template_name: str, operation_id: str) -> PresentationTemplate:
        template_root = files(self.package).joinpath(self.root, "shared")
        markdown_path = f"shared/{template_name}.md.jinja"
        structured_path = f"shared/{template_name}.json.jinja"
        if not template_root.joinpath(f"{template_name}.md.jinja").is_file():
            raise PresentationTemplateNotFound(operation_id)
        if not template_root.joinpath(f"{template_name}.json.jinja").is_file():
            raise PresentationTemplateNotFound(operation_id)
        return PresentationTemplate(
            operation_id=operation_id,
            application="shared",
            package=self.package,
            markdown_path=markdown_path,
            structured_path=structured_path,
        )
