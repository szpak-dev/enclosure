from collections.abc import Sequence
from dataclasses import dataclass, field
from operator import attrgetter

from modwire.application import ImplementationManifestDocument, ModwireApplication
from pydantic import ValidationError
from wireup import injectable

from ....errors import ProjectsError
from ..evidence.model import ImplementationContext, ImplementationEvidenceSet, ProviderManifest
from ..translators.base import ImplementationSemanticTranslator
from .base import ArchitectureEvidenceProvider


@injectable(as_type=ArchitectureEvidenceProvider, qualifier="modwire-evidence")
@dataclass(frozen=True)
class ModwireEvidenceProvider(ArchitectureEvidenceProvider):
    translators: Sequence[ImplementationSemanticTranslator]
    name: str = field(default="modwire", init=False)
    order: int = field(default=20, init=False)

    def collect(self, context: ImplementationContext) -> ImplementationEvidenceSet:
        application = ModwireApplication.create()
        try:
            document = ImplementationManifestDocument.model_validate(context.implementation_document)
        except ValidationError as error:
            raise ProjectsError(str(error)) from error
        if document.format not in application.implementation_manifest_formats():
            raise ProjectsError(f"Modwire manifest format {document.format.id!r} is not registered.")
        try:
            manifest = application.read_implementation_manifest(document)
        except ValidationError as error:
            raise ProjectsError(str(error)) from error
        candidates = tuple(
            translator
            for translator in sorted(self.translators, key=attrgetter("order", "provider", "language"))
            if translator.provider == self.name and translator.language == manifest.producer.extractor.language
        )
        if len(candidates) != 1:
            raise ProjectsError(
                f"Implementation evidence requires exactly one {self.name!r} translator for "
                f"{manifest.producer.extractor.language!r}."
            )
        return candidates[0].translate(
            ProviderManifest(
                provider=self.name,
                language=manifest.producer.extractor.language,
                version=manifest.producer.modwire_version,
                source_digest=manifest.source_manifest.digest,
                payload=manifest,
            )
        )
