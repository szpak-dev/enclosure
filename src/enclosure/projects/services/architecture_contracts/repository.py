from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from wireup import injectable

from ... import models
from ...errors import ProjectsError
from ..adapters.model import ResolvedArchitectureDiagram
from .model import (
    ArchitectureContractDiagram,
    ArchitectureContractExclusion,
    ArchitectureContractPublication,
    ArchitectureContractUnit,
    ArchitectureContractUnitInput,
)


@injectable
@dataclass
class ArchitectureContractRepository:
    model: type[models.ArchitectureContractPublication] = field(
        default=models.ArchitectureContractPublication,
        init=False,
    )

    def publish(
        self,
        project_id: str,
        authority: str,
        revision: str,
        units: tuple[tuple[ArchitectureContractUnitInput, tuple[ResolvedArchitectureDiagram, ...]], ...],
    ) -> ArchitectureContractPublication:
        try:
            with transaction.atomic():
                project = models.Project.objects.select_for_update().get(pk=project_id)
                version = project.architecture_contract_publications.count() + 1
                publication = self.model.objects.create(
                    project=project,
                    version=version,
                    authority=authority,
                    revision=revision,
                )
                for unit_position, resolved_unit in enumerate(units):
                    unit_input, resolved_diagrams = resolved_unit
                    unit = models.ArchitectureContractUnit.objects.create(
                        publication=publication,
                        key=unit_input.key,
                        diagram_set_id=unit_input.diagram_set_id,
                        source_root=unit_input.source_root,
                        coverage=unit_input.coverage.value,
                        position=unit_position,
                    )
                    models.ArchitectureContractDiagram.objects.bulk_create(
                        models.ArchitectureContractDiagram(
                            unit=unit,
                            diagram_id=resolved.diagram_id,
                            diagram_revision=resolved.revision,
                            role=diagram_input.role.value,
                            scope=diagram_input.scope.value,
                            kind=resolved.kind,
                            snapshot_version=resolved.snapshot_version,
                            registry_fingerprint=resolved.registry_fingerprint,
                            snapshot_digest=resolved.snapshot_digest,
                            snapshot=resolved.snapshot,
                            position=diagram_position,
                        )
                        for diagram_position, (diagram_input, resolved) in enumerate(
                            zip(unit_input.diagrams, resolved_diagrams, strict=True)
                        )
                    )
                    models.ArchitectureContractExclusion.objects.bulk_create(
                        models.ArchitectureContractExclusion(
                            unit=unit,
                            path=exclusion.path,
                            reason=exclusion.reason,
                            position=exclusion_position,
                        )
                        for exclusion_position, exclusion in enumerate(unit_input.exclusions)
                    )
                return self.get(project_id, str(publication.id))
        except IntegrityError as error:
            raise ProjectsError("This architecture contract has already been published.") from error

    def get(self, project_id: str, publication_id: str) -> ArchitectureContractPublication:
        try:
            publication = self.model.objects.get(pk=publication_id, project_id=project_id)
        except (self.model.DoesNotExist, ValidationError) as error:
            raise ProjectsError("Architecture contract publication does not exist for this project.") from error
        units = []
        for unit in publication.units.order_by("position"):
            diagrams = tuple(
                ArchitectureContractDiagram(
                    id=str(diagram.id),
                    diagram_id=diagram.diagram_id,
                    diagram_revision=diagram.diagram_revision,
                    role=diagram.role,
                    scope=diagram.scope,
                    kind=diagram.kind,
                    snapshot_version=diagram.snapshot_version,
                    registry_fingerprint=diagram.registry_fingerprint,
                    snapshot_digest=diagram.snapshot_digest,
                    snapshot=diagram.snapshot,
                    position=diagram.position,
                )
                for diagram in unit.diagrams.order_by("position")
            )
            exclusions = tuple(
                ArchitectureContractExclusion(
                    id=str(exclusion.id),
                    path=exclusion.path,
                    reason=exclusion.reason,
                    position=exclusion.position,
                )
                for exclusion in unit.exclusions.order_by("position")
            )
            units.append(
                ArchitectureContractUnit(
                    id=str(unit.id),
                    key=unit.key,
                    diagram_set_id=unit.diagram_set_id,
                    source_root=unit.source_root,
                    coverage=unit.coverage,
                    position=unit.position,
                    diagrams=diagrams,
                    exclusions=exclusions,
                )
            )
        return ArchitectureContractPublication(
            id=str(publication.id),
            project_id=str(publication.project_id),
            version=publication.version,
            authority=publication.authority,
            revision=publication.revision,
            units=tuple(units),
        )
