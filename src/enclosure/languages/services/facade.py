from collections.abc import Collection, Sequence
from dataclasses import dataclass

from wireup import injectable

from enclosure.shared import DiagramsService
from enclosure.shared.source_code.extraction import SourceExtractionService

from ..errors import LanguageDoesNotExist
from .base import Language, PackageManager
from .errors import LanguagesError


@injectable
@dataclass(frozen=True)
class LanguagesService:
    languages: Sequence[Language]
    extraction: SourceExtractionService
    diagrams: DiagramsService

    def find_all(self) -> list[Language]:
        return sorted(self.languages, key=lambda language: language.id)

    def get(self, language_id: str) -> Language:
        for language in self.languages:
            if language.id == language_id:
                return language
        raise LanguageDoesNotExist(language_id)

    def get_extensions(self, language: str) -> list[str]:
        return list(self.get(language).source_extensions)

    def get_ids(self) -> list[str]:
        return [language.id for language in self.languages]

    def recognize_package_manager(self, paths: Collection[str]) -> tuple[Language, PackageManager]:
        for path_attribute in ("lockfile_paths", "manifest_paths"):
            matches = [
                (language, package_manager)
                for language in self.languages
                for package_manager in language.package_managers
                if any(path in paths for path in getattr(package_manager, path_attribute))
            ]
            if len(matches) == 1:
                return matches[0]
            if matches:
                names = ", ".join(f"{language.id}/{package_manager.id}" for language, package_manager in matches)
                raise LanguagesError(f"Ambiguous package manager: {names}")

        raise LanguagesError("Package manager could not be recognized.")

    def validate_source(self, language: str, path: str, content: str) -> None:
        supported_language = self.get(language)
        extensions = supported_language.source_extensions

        if not path.endswith(tuple(extensions)):
            raise LanguagesError(f"Source path {path!r} not match {language!r}.")

        supported_language.validate(path, content)
        if language == "mermaid":
            self.diagrams.recognize(content)

        if supported_language.requires_extraction:
            self.extraction.validate(supported_language.id, path, content)
