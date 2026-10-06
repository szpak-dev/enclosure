from dataclasses import dataclass, field
from importlib.metadata import version

from wireup import injectable

from enclosure.diagnostics.services import CacheDiagnosticsContext

from ....errors import ProjectsError
from ...architecture_manifests.bindings.model import ArchitectureRealizationMap
from ...architecture_manifests.evidence.model import ImplementationContext, ImplementationEvidenceManifest
from ...architecture_manifests.model import ArchitectureComparison, ArchitectureComparisonConclusion
from ...architecture_manifests.providers.base import ArchitectureArtifactObserver
from ...architecture_manifests.service import ArchitectureManifestService
from ...reports.adapters.architecture import ArchitectureAdapter
from ...reports.model import ArchitectureObservation, ArchitectureReportObservation
from ..attestations.identity import ArchitectureConformanceIdentity
from ..attestations.model import (
    ArchitectureAttestationContext,
    ArchitectureConformanceAttestation,
    ArchitectureFindingAttestationEvidence,
)
from ..attestations.service import ArchitectureAttestationService
from ..conformance.model import ArchitectureHealthInputIdentity
from ..conformance.service import ArchitectureConformanceService
from .cache import HealthCacheIdentityService
from .diagnostics import HealthPhaseDiagnostics
from .gateway import ArchitectureHealthCache
from .model import (
    CacheOutcomeState,
    CompletedHealthExecutionResult,
    HealthCacheComponent,
    HealthCacheIdentity,
    HealthCacheStage,
    HealthExecutionPhase,
    HealthExecutionRequest,
)


@injectable
@dataclass(frozen=True)
class HealthWorkerEvaluationService:
    architecture: ArchitectureAdapter
    artifacts: ArchitectureArtifactObserver
    manifests: ArchitectureManifestService
    conformance: ArchitectureConformanceService
    attestations: ArchitectureAttestationService
    cache: CacheDiagnosticsContext
    health_cache: ArchitectureHealthCache
    cache_identities: HealthCacheIdentityService
    phases: HealthPhaseDiagnostics
    identity: ArchitectureConformanceIdentity = field(default_factory=ArchitectureConformanceIdentity, init=False)

    def evaluate(self, request: HealthExecutionRequest) -> CompletedHealthExecutionResult:
        self.cache.begin()
        phase_tokens = self.phases.begin()
        try:
            source_phase = self.phases.start(HealthExecutionPhase.SOURCE_INVENTORY)
            source_digest = self.architecture.source_identity(request.source)
            self.phases.finish(source_phase, item_count=1)

            artifact_phase = self.phases.start(HealthExecutionPhase.ARTIFACT_INVENTORY)
            artifact_plan = self.artifacts.plan(request.contract.manifest)
            artifact_inventory = self.artifacts.observe(request.source.architecture_root, artifact_plan)
            self.phases.finish(artifact_phase, item_count=len(artifact_inventory.observations))

            completed_identity = self.cache_identities.identity(
                HealthCacheStage.COMPLETED_RESULT,
                (
                    HealthCacheComponent(name="modwire-source", digest=source_digest),
                    HealthCacheComponent(name="artifact-inventory", digest=artifact_inventory.digest),
                    HealthCacheComponent(name="configuration", digest=request.contract.configuration_revision),
                    HealthCacheComponent(name="architecture-contract", digest=request.contract.manifest.digest),
                    HealthCacheComponent(
                        name="operating-contract",
                        digest=(
                            f"{request.contract.operating_contract.contract_id}:"
                            f"{request.contract.operating_contract.version}"
                        ),
                    ),
                    HealthCacheComponent(name="update-policy", digest=request.contract.update_policy.value),
                    HealthCacheComponent(name="modwire", digest=version("modwire")),
                    HealthCacheComponent(name="conformance-engine", digest=self.identity.model_dump_json()),
                    HealthCacheComponent(name="implementation-document-engine", digest="canonical-json-v2"),
                    HealthCacheComponent(name="report-engine", digest="modwire-report-v1"),
                    HealthCacheComponent(name="evidence-engine", digest="typed-artifact-evidence-v2"),
                    HealthCacheComponent(name="binding-engine", digest="indexed-binding-v1"),
                    HealthCacheComponent(name="completed-result-schema", digest="2"),
                ),
            )
            cache_phase = self.phases.start(HealthExecutionPhase.COMPLETED_RESULT_CACHE)
            cached = self.health_cache.load(completed_identity)
            if cached.state == CacheOutcomeState.HIT:
                try:
                    result = CompletedHealthExecutionResult.model_validate_json(cached.payload)
                except ValueError:
                    cached = cached.model_copy(
                        update={
                            "state": CacheOutcomeState.CORRUPT,
                            "payload": b"",
                            "detail": "Health cache payload violates the completed-result schema.",
                        }
                    )
                else:
                    self.phases.finish(
                        cache_phase,
                        cache_outcome=CacheOutcomeState.HIT,
                        cache_stages=(HealthCacheStage.COMPLETED_RESULT,),
                    )
                    return result.model_copy(
                        update={
                            "cache_outcomes": (),
                            "phase_diagnostics": self.phases.read(),
                        }
                    )
            self.phases.finish(
                cache_phase,
                cache_outcome=cached.state,
                cache_stages=(HealthCacheStage.COMPLETED_RESULT,),
            )

            deferred_stores: list[tuple[HealthCacheIdentity, bytes]] = []
            observation_identity = self.cache_identities.identity(
                HealthCacheStage.IMPLEMENTATION_DOCUMENT,
                (
                    HealthCacheComponent(name="modwire-source", digest=source_digest),
                    HealthCacheComponent(name="language", digest=request.source.language),
                    HealthCacheComponent(name="modwire", digest=version("modwire")),
                    HealthCacheComponent(name="implementation-document-schema", digest="canonical-json"),
                    HealthCacheComponent(name="implementation-document-engine", digest="canonical-json-v2"),
                ),
            )
            observations: tuple[ArchitectureObservation, ...] = ()
            implementation_lookup_phase = self.phases.start(HealthExecutionPhase.IMPLEMENTATION_MANIFEST)
            observation_lookup = self.health_cache.load(observation_identity)
            if observation_lookup.state == CacheOutcomeState.HIT:
                try:
                    observations = (ArchitectureObservation.model_validate_json(observation_lookup.payload),)
                except ValueError:
                    observation_lookup = observation_lookup.model_copy(
                        update={"state": CacheOutcomeState.CORRUPT, "payload": b""}
                    )
            self.phases.finish(
                implementation_lookup_phase,
                outcome="cache-lookup",
                item_count=len(observations[0].implementation_document) if observations else 0,
                cache_outcome=observation_lookup.state,
                cache_stages=(HealthCacheStage.IMPLEMENTATION_DOCUMENT,),
            )

            reports_identity = self.cache_identities.identity(
                HealthCacheStage.MODWIRE_REPORTS,
                (
                    HealthCacheComponent(name="modwire-source", digest=source_digest),
                    HealthCacheComponent(name="configuration", digest=request.contract.configuration_revision),
                    HealthCacheComponent(name="modwire", digest=version("modwire")),
                    HealthCacheComponent(name="report-engine", digest="modwire-report-v1"),
                ),
            )
            report_observations: tuple[ArchitectureReportObservation, ...] = ()
            reports_lookup_phase = self.phases.start(HealthExecutionPhase.MODWIRE_REPORTS)
            reports_lookup = self.health_cache.load(reports_identity)
            if reports_lookup.state == CacheOutcomeState.HIT:
                try:
                    report_observations = (ArchitectureReportObservation.model_validate_json(reports_lookup.payload),)
                except ValueError:
                    reports_lookup = reports_lookup.model_copy(
                        update={"state": CacheOutcomeState.CORRUPT, "payload": b""}
                    )
            self.phases.finish(
                reports_lookup_phase,
                outcome="cache-lookup",
                item_count=len(report_observations[0].reports) if report_observations else 0,
                cache_outcome=reports_lookup.state,
                cache_stages=(HealthCacheStage.MODWIRE_REPORTS,),
            )
            if observations and observations[0].source_digest != source_digest:
                raise ProjectsError("Project source changed during health evaluation.")
            if report_observations and report_observations[0].source_digest != source_digest:
                raise ProjectsError("Project source changed during health evaluation.")
            if not observations or not report_observations:
                code_map_phase = self.phases.start(HealthExecutionPhase.MODWIRE_CODE_MAP)
                code_map_observation = self.architecture.code_map(request.source)
                if code_map_observation.source_digest != source_digest:
                    raise ProjectsError("Project source changed during health evaluation.")
                self.phases.finish(code_map_phase, item_count=1)
                if not observations:
                    implementation_phase = self.phases.start(HealthExecutionPhase.IMPLEMENTATION_MANIFEST)
                    observation = self.architecture.observe(code_map_observation)
                    observations = (observation,)
                    deferred_stores.append((observation_identity, observation.model_dump_json().encode("utf-8")))
                    self.phases.finish(
                        implementation_phase,
                        outcome="computed",
                        item_count=len(observation.implementation_document),
                    )
                if not report_observations:
                    reports_phase = self.phases.start(HealthExecutionPhase.MODWIRE_REPORTS)
                    report_observation = self.architecture.observe_reports(request.source, code_map_observation)
                    report_observations = (report_observation,)
                    deferred_stores.append((reports_identity, report_observation.model_dump_json().encode("utf-8")))
                    self.phases.finish(
                        reports_phase,
                        outcome="computed",
                        item_count=len(report_observation.reports),
                    )
            observation = observations[0]
            report_observation = report_observations[0]
            reports = tuple(report for report in report_observation.reports if "violations" in report)

            evidence_identity = self.cache_identities.identity(
                HealthCacheStage.IMPLEMENTATION_EVIDENCE,
                (
                    HealthCacheComponent(name="implementation-document", digest=observation.document_digest),
                    HealthCacheComponent(name="artifact-inventory", digest=artifact_inventory.digest),
                    HealthCacheComponent(name="evidence-schema", digest="2"),
                    HealthCacheComponent(name="evidence-engine", digest="typed-artifact-evidence-v2"),
                ),
            )
            implementations: tuple[ImplementationEvidenceManifest, ...] = ()
            evidence_lookup_phase = self.phases.start(HealthExecutionPhase.EVIDENCE)
            evidence_lookup = self.health_cache.load(evidence_identity)
            if evidence_lookup.state == CacheOutcomeState.HIT:
                try:
                    implementations = (ImplementationEvidenceManifest.model_validate_json(evidence_lookup.payload),)
                except ValueError:
                    evidence_lookup = evidence_lookup.model_copy(
                        update={"state": CacheOutcomeState.CORRUPT, "payload": b""}
                    )
            self.phases.finish(
                evidence_lookup_phase,
                outcome="cache-lookup",
                item_count=len(implementations[0].evidence) if implementations else 0,
                cache_outcome=evidence_lookup.state,
                cache_stages=(HealthCacheStage.IMPLEMENTATION_EVIDENCE,),
            )
            if not implementations:
                evidence_phase = self.phases.start(HealthExecutionPhase.EVIDENCE)
                implementation = self.manifests.collect_evidence(
                    ImplementationContext(
                        implementation_document=observation.implementation_document,
                        artifact_inventory=artifact_inventory,
                    )
                )
                implementations = (implementation,)
                deferred_stores.append((evidence_identity, implementation.model_dump_json().encode("utf-8")))
                self.phases.finish(
                    evidence_phase,
                    outcome="computed",
                    item_count=len(implementation.evidence),
                )
            implementation = implementations[0]

            realization_identity = self.cache_identities.identity(
                HealthCacheStage.REALIZATION,
                (
                    HealthCacheComponent(name="architecture-contract", digest=request.contract.manifest.digest),
                    HealthCacheComponent(name="implementation-evidence", digest=implementation.digest),
                    HealthCacheComponent(name="binding-engine", digest="indexed-binding-v1"),
                ),
            )
            realizations: tuple[ArchitectureRealizationMap, ...] = ()
            realization_lookup_phase = self.phases.start(HealthExecutionPhase.REALIZATION)
            realization_lookup = self.health_cache.load(realization_identity)
            if realization_lookup.state == CacheOutcomeState.HIT:
                try:
                    realizations = (ArchitectureRealizationMap.model_validate_json(realization_lookup.payload),)
                except ValueError:
                    realization_lookup = realization_lookup.model_copy(
                        update={"state": CacheOutcomeState.CORRUPT, "payload": b""}
                    )
            self.phases.finish(
                realization_lookup_phase,
                outcome="cache-lookup",
                item_count=len(realizations[0].bindings) if realizations else 0,
                cache_outcome=realization_lookup.state,
                cache_stages=(HealthCacheStage.REALIZATION,),
            )
            if not realizations:
                realization_phase = self.phases.start(HealthExecutionPhase.REALIZATION)
                realization = self.manifests.realize(request.contract.manifest, implementation)
                realizations = (realization,)
                deferred_stores.append((realization_identity, realization.model_dump_json().encode("utf-8")))
                self.phases.finish(
                    realization_phase,
                    outcome="computed",
                    item_count=len(realization.bindings),
                )
            realization = realizations[0]

            comparison_identity = self.cache_identities.identity(
                HealthCacheStage.COMPARISON,
                (
                    HealthCacheComponent(name="architecture-contract", digest=request.contract.manifest.digest),
                    HealthCacheComponent(name="implementation-evidence", digest=implementation.digest),
                    HealthCacheComponent(name="realization", digest=realization.digest),
                    HealthCacheComponent(
                        name="comparator",
                        digest=self.identity.comparison.model_dump_json(),
                    ),
                ),
            )
            comparisons: tuple[ArchitectureComparison, ...] = ()
            comparison_lookup_phase = self.phases.start(HealthExecutionPhase.COMPARISON)
            comparison_lookup = self.health_cache.load(comparison_identity)
            if comparison_lookup.state == CacheOutcomeState.HIT:
                try:
                    comparisons = (ArchitectureComparison.model_validate_json(comparison_lookup.payload),)
                except ValueError:
                    comparison_lookup = comparison_lookup.model_copy(
                        update={"state": CacheOutcomeState.CORRUPT, "payload": b""}
                    )
            self.phases.finish(
                comparison_lookup_phase,
                outcome="cache-lookup",
                item_count=len(comparisons[0].results) if comparisons else 0,
                cache_outcome=comparison_lookup.state,
                cache_stages=(HealthCacheStage.COMPARISON,),
            )
            if not comparisons:
                comparison_phase = self.phases.start(HealthExecutionPhase.COMPARISON)
                comparison = self.manifests.compare_evidence(
                    request.contract.manifest,
                    implementation,
                    realization,
                )
                comparisons = (comparison,)
                deferred_stores.append((comparison_identity, comparison.model_dump_json().encode("utf-8")))
                self.phases.finish(
                    comparison_phase,
                    outcome="computed",
                    item_count=len(comparison.results),
                )
            comparison = comparisons[0]
            conformance = self.conformance.project(comparison)

            attestation_identity = self.cache_identities.identity(
                HealthCacheStage.ATTESTATION,
                (
                    HealthCacheComponent(name="comparison", digest=comparison.digest),
                    HealthCacheComponent(
                        name="operating-contract",
                        digest=(
                            f"{request.contract.operating_contract.contract_id}:"
                            f"{request.contract.operating_contract.version}"
                        ),
                    ),
                    HealthCacheComponent(name="update-policy", digest=request.contract.update_policy.value),
                    HealthCacheComponent(name="configuration", digest=request.contract.configuration_revision),
                    HealthCacheComponent(name="attestation-engine", digest=self.identity.model_dump_json()),
                ),
            )
            attestations: tuple[ArchitectureConformanceAttestation, ...] = ()
            attestation_lookup_phase = self.phases.start(HealthExecutionPhase.ATTESTATION)
            attestation_lookup = self.health_cache.load(attestation_identity)
            if attestation_lookup.state == CacheOutcomeState.HIT:
                try:
                    attestations = (ArchitectureConformanceAttestation.model_validate_json(attestation_lookup.payload),)
                except ValueError:
                    attestation_lookup = attestation_lookup.model_copy(
                        update={"state": CacheOutcomeState.CORRUPT, "payload": b""}
                    )
            self.phases.finish(
                attestation_lookup_phase,
                outcome="cache-lookup",
                item_count=len(attestations[0].components) if attestations else 0,
                cache_outcome=attestation_lookup.state,
                cache_stages=(HealthCacheStage.ATTESTATION,),
            )
            if not attestations:
                attestation_phase = self.phases.start(HealthExecutionPhase.ATTESTATION)
                attestation = self.attestations.attest(
                    ArchitectureAttestationContext(
                        contract=request.contract.manifest,
                        implementation=implementation,
                        realization=realization,
                        comparison=comparison,
                        findings=tuple(
                            ArchitectureFindingAttestationEvidence(
                                fingerprint=finding.fingerprint,
                                owner=finding.owner,
                                kind=finding.finding_kind,
                                message=finding.message,
                                next_action=finding.next_action,
                            )
                            for finding in conformance.findings
                        ),
                        operating_contract=request.contract.operating_contract,
                        update_policy=request.contract.update_policy,
                        configuration_revision=request.contract.configuration_revision,
                        identity=self.identity,
                    )
                )
                attestations = (attestation,)
                deferred_stores.append((attestation_identity, attestation.model_dump_json().encode("utf-8")))
                self.phases.finish(
                    attestation_phase,
                    outcome="computed",
                    item_count=len(attestation.components),
                )
            attestation = attestations[0]
            result = CompletedHealthExecutionResult(
                healthy=(
                    all(not report["violations"] for report in reports)
                    and conformance.conclusion == ArchitectureComparisonConclusion.CONFORMS
                ),
                reports=reports,
                conformance=conformance,
                attestation=attestation,
                input_identity=ArchitectureHealthInputIdentity(
                    modwire_source_digest=observation.source_digest,
                    artifact_inventory_digest=artifact_inventory.digest,
                    provider_receipts=implementation.provider_receipts,
                    digest=implementation.source_digest,
                ),
                cache_outcomes=self.cache.read(),
                phase_diagnostics=self.phases.read(),
                detail="",
            )
            cached_result = result.model_copy(update={"cache_outcomes": (), "phase_diagnostics": ()})
            deferred_stores.append((completed_identity, cached_result.model_dump_json().encode("utf-8")))
            for identity, payload in deferred_stores:
                persistence_phase = self.phases.start(HealthExecutionPhase.CACHE_PERSISTENCE)
                store_outcome = self.health_cache.store(identity, payload)
                self.phases.finish(
                    persistence_phase,
                    item_count=1,
                    cache_outcome=store_outcome,
                    cache_stages=(identity.stage,),
                )
            return result.model_copy(update={"phase_diagnostics": self.phases.read()})
        finally:
            self.cache.reset()
            self.phases.reset(phase_tokens)
