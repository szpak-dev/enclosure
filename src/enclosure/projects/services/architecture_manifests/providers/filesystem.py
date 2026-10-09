import json
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import cast

from wireup import injectable

from ....errors import ProjectsError
from ...architecture_contracts.model import ArchitectureContractCoverage
from ..assertions.model import ArchitectureArtifactKind, ArchitectureAssertionKind, ArtifactAssertion
from ..evidence.identity import ArtifactObservationManifestIdentity
from ..evidence.model import (
    ArchitectureSupportState,
    ArtifactObservation,
    ArtifactObservationManifest,
    ArtifactObservationPlan,
    ArtifactObservationScope,
)
from ..model import ArchitectureContractManifest
from .base import ArchitectureArtifactObserver


@injectable(as_type=ArchitectureArtifactObserver)
@dataclass(frozen=True)
class FilesystemArtifactObserver(ArchitectureArtifactObserver):
    identity: ArtifactObservationManifestIdentity

    def plan(self, contract: ArchitectureContractManifest) -> ArtifactObservationPlan:
        scopes = tuple(
            ArtifactObservationScope(
                unit_key=unit.key,
                source_root=unit.source_root,
                coverage=unit.coverage,
                exclusions=unit.exclusions,
                declared_artifacts=tuple(
                    cast(ArtifactAssertion, assertion)
                    for assertion in unit.assertions
                    if assertion.kind == ArchitectureAssertionKind.ARTIFACT
                ),
            )
            for unit in contract.units
        )
        payload = {"scopes": [scope.model_dump(mode="json") for scope in scopes]}
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ArtifactObservationPlan(scopes=scopes, digest=sha256(canonical.encode("utf-8")).hexdigest())

    def observe(self, root: str, plan: ArtifactObservationPlan) -> ArtifactObservationManifest:
        architecture_root = Path(root).resolve()
        observations: dict[tuple[str, ArchitectureArtifactKind], ArtifactObservation] = {}
        for scope in plan.scopes:
            scope_observations = (
                self.declared_observations(architecture_root, scope)
                if scope.coverage == ArchitectureContractCoverage.DECLARED
                else self.closed_observations(architecture_root, scope)
            )
            for observation in scope_observations:
                observations[(observation.path, observation.artifact_kind)] = observation
        ordered = tuple(observations[key] for key in sorted(observations, key=lambda item: (item[0], item[1].value)))
        return self.identity.manifest(
            support=ArchitectureSupportState.SUPPORTED,
            plan_digest=plan.digest,
            observations=ordered,
        )

    def verify(self, root: str, plan: ArtifactObservationPlan, expected_digest: str) -> None:
        if self.observe(root, plan).digest != expected_digest:
            raise ProjectsError("Project artifacts changed during health evaluation.")

    def declared_observations(
        self,
        root: Path,
        scope: ArtifactObservationScope,
    ) -> tuple[ArtifactObservation, ...]:
        return tuple(self.declared_observation(root, assertion) for assertion in scope.declared_artifacts)

    def declared_observation(self, root: Path, assertion: ArtifactAssertion) -> ArtifactObservation:
        path = self.inside(root, assertion.path)
        if not path.exists():
            return ArtifactObservation(
                path=assertion.path,
                artifact_kind=assertion.artifact_kind,
                exists=False,
                content_digest="",
            )
        artifact_kind = self.artifact_kind(path)
        return ArtifactObservation(
            path=assertion.path,
            artifact_kind=artifact_kind,
            exists=True,
            content_digest=self.content_digest(path, artifact_kind),
        )

    def closed_observations(
        self,
        root: Path,
        scope: ArtifactObservationScope,
    ) -> tuple[ArtifactObservation, ...]:
        scope_root = root / scope.source_root
        self.inside(root, scope.source_root)
        if not scope_root.exists():
            return ()
        excluded = tuple(exclusion.path for exclusion in scope.exclusions)
        if self.excluded(scope.source_root, excluded):
            return ()
        observed: list[ArtifactObservation] = [self.observation(root, scope_root)]
        for current, directories, files in os.walk(scope_root, topdown=True, followlinks=False):
            current_path = Path(current)
            current_relative = current_path.relative_to(root).as_posix()
            retained_directories: list[str] = []
            for directory in sorted(directories):
                directory_path = current_path / directory
                relative = self.relative(root, directory_path)
                if self.excluded(relative, excluded):
                    continue
                self.inside(root, relative)
                if directory_path.is_symlink():
                    observed.append(self.observation(root, directory_path))
                else:
                    retained_directories.append(directory)
            directories[:] = retained_directories
            if current_relative != scope.source_root and not self.excluded(current_relative, excluded):
                observed.append(self.observation(root, current_path))
            observed.extend(
                self.observation(root, current_path / file)
                for file in sorted(files)
                if not self.excluded(self.relative(root, current_path / file), excluded)
            )
        return tuple(observed)

    def observation(self, root: Path, path: Path) -> ArtifactObservation:
        relative = self.relative(root, path)
        safe = self.inside(root, relative)
        artifact_kind = self.artifact_kind(safe)
        return ArtifactObservation(
            path=relative,
            artifact_kind=artifact_kind,
            exists=True,
            content_digest=self.content_digest(safe, artifact_kind),
        )

    def inside(self, root: Path, relative: str) -> Path:
        candidate = root / relative
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            raise ProjectsError(f"Architecture artifact path escapes the workspace: {relative!r}.")
        return resolved

    def relative(self, root: Path, path: Path) -> str:
        return path.relative_to(root).as_posix()

    def excluded(self, path: str, exclusions: tuple[str, ...]) -> bool:
        return any(path == exclusion or path.startswith(f"{exclusion}/") for exclusion in exclusions)

    def artifact_kind(self, path: Path) -> ArchitectureArtifactKind:
        if path.is_file():
            return ArchitectureArtifactKind.FILE
        if path.is_dir():
            return ArchitectureArtifactKind.DIRECTORY
        raise ProjectsError(f"Unsupported architecture artifact kind: {path}.")

    def content_digest(self, path: Path, artifact_kind: ArchitectureArtifactKind) -> str:
        if artifact_kind == ArchitectureArtifactKind.DIRECTORY:
            return ""
        digest = sha256()
        with path.open("rb") as artifact:
            while chunk := artifact.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()
