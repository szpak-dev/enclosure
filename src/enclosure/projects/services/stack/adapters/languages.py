from dataclasses import dataclass

from wireup import injectable

from enclosure.languages.services import LanguagesService
from enclosure.shared import FilesPackage

from ..model import DetectedStack


@injectable
@dataclass(frozen=True)
class LanguagesAdapter:
    languages: LanguagesService

    def sniff_project(self, files: FilesPackage) -> DetectedStack:
        language, package_manager = self.languages.recognize_package_manager(files.mapping.keys())
        return DetectedStack(
            language=language.id,
            language_version=language.stable_version,
            package_manager=package_manager.id,
        )
