from collections.abc import Mapping
from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from wireup import injectable

from ... import models
from ...errors import ProjectsError
from ..contracts.model import OperatingContractReference


@injectable
@dataclass
class OperatingContractRepository:
    model: type[models.OperatingContract] = field(default=models.OperatingContract, init=False)

    def create(self, data: Mapping[str, str]) -> models.OperatingContract:
        try:
            with transaction.atomic():
                return self.model.objects.create(**data)
        except IntegrityError as error:
            raise ProjectsError("An operating contract with this authority already exists.") from error

    def get_contract(self, contract_id: str) -> models.OperatingContract:
        return self.model.objects.get(pk=contract_id)

    @transaction.atomic
    def create_revision(
        self,
        contract: models.OperatingContract,
        references: tuple[OperatingContractReference, ...],
    ) -> models.OperatingContractRevision:
        locked_contract = self.model.objects.select_for_update().get(pk=contract.id)
        current = locked_contract.revisions.order_by("-version").first()
        version = 1 if current is None else current.version + 1
        revision = models.OperatingContractRevision.objects.create(
            contract=locked_contract,
            version=version,
        )
        guidance = []
        external = []
        for position, reference in enumerate(references):
            if reference.kind == "guidance":
                guidance.append(
                    models.OperatingContractGuidance(
                        revision=revision,
                        record_id=reference.id,
                        record_revision=reference.revision,
                        authority=reference.authority,
                        position=position,
                    )
                )
                continue
            external.append(
                models.OperatingContractReference(
                    revision=revision,
                    kind=reference.kind,
                    target_id=reference.id,
                    authority=reference.authority,
                    target_revision=reference.revision,
                    position=position,
                )
            )
        models.OperatingContractGuidance.objects.bulk_create(guidance)
        models.OperatingContractReference.objects.bulk_create(external)
        return self.get_revision(locked_contract.id, version)

    def get_revision(self, contract_id: str, version: int) -> models.OperatingContractRevision:
        return self._revisions().get(contract_id=contract_id, version=version)

    def get_latest_revision(self, contract_id: str) -> models.OperatingContractRevision:
        return self._revisions().filter(contract_id=contract_id).latest("version")

    def create_binding(
        self,
        project_id: str,
        revision: models.OperatingContractRevision,
        update_policy: str,
    ) -> models.OperatingContractBinding:
        try:
            with transaction.atomic():
                return models.OperatingContractBinding.objects.create(
                    project_id=project_id,
                    bound_revision=revision,
                    update_policy=update_policy,
                )
        except IntegrityError as error:
            raise ProjectsError(
                "The project already has an operating contract. Replace its binding explicitly."
            ) from error

    def replace_binding(
        self,
        project_id: str,
        revision: models.OperatingContractRevision,
        update_policy: str,
    ) -> models.OperatingContractBinding:
        binding = self.get_binding(project_id)
        binding.bound_revision = revision
        binding.update_policy = update_policy
        binding.save(update_fields=("bound_revision", "update_policy"))
        return self.get_binding(project_id)

    def has_binding(self, project_id: str) -> bool:
        return models.OperatingContractBinding.objects.filter(project_id=project_id).exists()

    def get_binding(self, project_id: str) -> models.OperatingContractBinding:
        return models.OperatingContractBinding.objects.select_related(
            "project",
            "bound_revision__contract",
        ).get(project_id=project_id)

    def _revisions(self):
        return models.OperatingContractRevision.objects.select_related("contract").prefetch_related(
            "guidance_references",
            "contract_references",
        )
