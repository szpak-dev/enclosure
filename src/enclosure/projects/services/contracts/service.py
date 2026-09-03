from dataclasses import dataclass
from typing import Literal

from wireup import injectable

from ... import models
from ...errors import ProjectsError
from ..adapters import RecordsAdapter
from .model import (
    ConfiguredOperatingContractBinding,
    OperatingContract,
    OperatingContractReference,
    OperatingContractRevision,
    UnconfiguredOperatingContractBinding,
)
from .repository import OperatingContractRepository


@injectable
@dataclass(frozen=True)
class OperatingContractsService:
    records: RecordsAdapter
    repository: OperatingContractRepository

    def create(self, title: str, authority: str, provenance: str) -> OperatingContract:
        if not title.strip() or not authority.strip() or not provenance.strip():
            raise ProjectsError("Operating contract title, authority, and provenance are required.")
        return self._contract(
            self.repository.create(
                {
                    "title": title,
                    "authority": authority,
                    "provenance": provenance,
                }
            )
        )

    def get(self, contract_id: str) -> OperatingContract:
        return self._contract(self.repository.get_contract(contract_id))

    def publish(
        self,
        contract_id: str,
        record_ids: tuple[str, ...],
        references: tuple[OperatingContractReference, ...],
    ) -> OperatingContractRevision:
        if not record_ids:
            raise ProjectsError("An operating contract revision requires mandatory guidance.")
        if len(record_ids) != len(set(record_ids)):
            raise ProjectsError("An operating contract revision cannot reference guidance more than once.")
        if any(reference.kind == "guidance" for reference in references):
            raise ProjectsError("Guidance references must be published through record identifiers.")

        resolution = self.records.resolve_guidance(
            record_ids,
        )
        if resolution.missing_ids:
            raise ProjectsError("Operating contract guidance must reference existing records.")

        guidance = tuple(
            OperatingContractReference(
                kind="guidance",
                id=item.id,
                authority=item.authority,
                revision=item.revision,
            )
            for item in resolution.guidance
        )
        combined = (*guidance, *references)
        identities = tuple((reference.kind, reference.id) for reference in combined)
        if len(identities) != len(set(identities)):
            raise ProjectsError("An operating contract revision cannot contain duplicate references.")
        if any(
            not reference.id.strip() or not reference.authority.strip() or not reference.revision.strip()
            for reference in combined
        ):
            raise ProjectsError("Operating contract references require identity, authority, and revision.")

        contract = self.repository.get_contract(contract_id)
        return self._revision(self.repository.create_revision(contract, combined))

    def get_revision(self, contract_id: str, version: int) -> OperatingContractRevision:
        return self._revision(self.repository.get_revision(contract_id, version))

    def bind(
        self,
        project_id: str,
        contract_id: str,
        version: int,
        update_policy: Literal["pinned", "follow-latest"],
    ) -> ConfiguredOperatingContractBinding:
        revision = self.repository.get_revision(contract_id, version)
        self.repository.create_binding(project_id, revision, update_policy)
        return self._configured_binding(project_id)

    def replace_binding(
        self,
        project_id: str,
        contract_id: str,
        version: int,
        update_policy: Literal["pinned", "follow-latest"],
    ) -> ConfiguredOperatingContractBinding:
        revision = self.repository.get_revision(contract_id, version)
        self.repository.replace_binding(project_id, revision, update_policy)
        return self._configured_binding(project_id)

    def get_binding(
        self,
        project_id: str,
    ) -> ConfiguredOperatingContractBinding | UnconfiguredOperatingContractBinding:
        if not self.repository.has_binding(project_id):
            return UnconfiguredOperatingContractBinding(project_id=project_id)
        return self._configured_binding(project_id)

    def bootstrap(
        self,
        project_id: str,
        record_ids: tuple[str, ...],
    ) -> ConfiguredOperatingContractBinding | UnconfiguredOperatingContractBinding:
        if not record_ids:
            return UnconfiguredOperatingContractBinding(project_id=project_id)
        contract = self.create(
            title="Project operating contract",
            authority=f"project:{project_id}:operating-contract",
            provenance="project-registration",
        )
        revision = self.publish(contract.id, record_ids, ())
        return self.bind(project_id, contract.id, revision.version, "follow-latest")

    def _configured_binding(self, project_id: str) -> ConfiguredOperatingContractBinding:
        binding = self.repository.get_binding(project_id)
        bound_revision = binding.bound_revision
        effective_revision = (
            bound_revision
            if binding.update_policy == models.OperatingContractBinding.UpdatePolicy.PINNED
            else self.repository.get_latest_revision(bound_revision.contract_id)
        )
        return ConfiguredOperatingContractBinding(
            project_id=project_id,
            contract=self._contract(bound_revision.contract),
            update_policy=binding.update_policy,
            bound_revision=bound_revision.version,
            effective_revision=self._revision(effective_revision),
        )

    def _contract(self, contract: models.OperatingContract) -> OperatingContract:
        return OperatingContract(
            id=contract.id,
            title=contract.title,
            authority=contract.authority,
            provenance=contract.provenance,
        )

    def _revision(self, revision: models.OperatingContractRevision) -> OperatingContractRevision:
        references = [
            (
                item.position,
                OperatingContractReference(
                    kind="guidance",
                    id=item.record_id,
                    authority=item.authority,
                    revision=item.record_revision,
                ),
            )
            for item in revision.guidance_references.all()
        ]
        references.extend(
            (
                item.position,
                OperatingContractReference(
                    kind=item.kind,
                    id=item.target_id,
                    authority=item.authority,
                    revision=item.target_revision,
                ),
            )
            for item in revision.contract_references.all()
        )
        return OperatingContractRevision(
            id=revision.id,
            contract_id=revision.contract_id,
            version=revision.version,
            references=tuple(reference for _, reference in sorted(references, key=lambda item: item[0])),
        )
