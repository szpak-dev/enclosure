import base64
import fcntl
import os
import tempfile
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from django.conf import settings
from pydantic import ValidationError
from wireup import injectable

from ..gateway import ArchitectureHealthCache
from ..model import CacheOutcomeState, HealthCacheEnvelope, HealthCacheIdentity, HealthCacheLookup


@injectable(as_type=ArchitectureHealthCache)
@dataclass(frozen=True)
class FilesystemArchitectureHealthCache(ArchitectureHealthCache):
    schema_version: int = field(default=1, init=False)

    def load(self, identity: HealthCacheIdentity) -> HealthCacheLookup:
        directory = Path(settings.PROJECT_HEALTH_CACHE_DIRECTORY)
        path = directory / identity.stage.value / f"{identity.digest}.json"
        if not path.is_file():
            return HealthCacheLookup(state=CacheOutcomeState.MISS)
        try:
            envelope = HealthCacheEnvelope.model_validate_json(path.read_bytes())
            if (
                envelope.schema_version != self.schema_version
                or envelope.stage != identity.stage
                or envelope.identity_digest != identity.digest
            ):
                return HealthCacheLookup(state=CacheOutcomeState.STALE, detail="Health cache identity mismatch.")
            payload = base64.b64decode(envelope.encoded_payload, validate=True)
            if sha256(payload).hexdigest() != envelope.payload_digest:
                return HealthCacheLookup(
                    state=CacheOutcomeState.CORRUPT, detail="Health cache payload digest mismatch."
                )
            os.utime(path, None)
            return HealthCacheLookup(state=CacheOutcomeState.HIT, payload=payload)
        except (ValidationError, ValueError):
            return HealthCacheLookup(state=CacheOutcomeState.CORRUPT, detail="Health cache entry is unreadable.")
        except OSError:
            return HealthCacheLookup(state=CacheOutcomeState.UNAVAILABLE, detail="Health cache storage is unavailable.")

    def store(self, identity: HealthCacheIdentity, payload: bytes) -> CacheOutcomeState:
        envelope = HealthCacheEnvelope(
            schema_version=self.schema_version,
            stage=identity.stage,
            identity_digest=identity.digest,
            payload_digest=sha256(payload).hexdigest(),
            encoded_payload=base64.b64encode(payload).decode("ascii"),
        )
        encoded = envelope.model_dump_json().encode("utf-8")
        if len(encoded) > settings.PROJECT_HEALTH_CACHE_MAX_BYTES:
            return CacheOutcomeState.UNAVAILABLE
        try:
            directory = Path(settings.PROJECT_HEALTH_CACHE_DIRECTORY)
            path = directory / identity.stage.value / f"{identity.digest}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            lock_path = directory / ".maintenance.lock"
            directory.mkdir(parents=True, exist_ok=True)
            with lock_path.open("a+b") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                temporary_name = ""
                try:
                    for orphan in directory.glob("*/.health-*"):
                        if orphan.is_file():
                            orphan.unlink()
                    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".health-", delete=False) as temporary:
                        temporary_name = temporary.name
                        temporary.write(encoded)
                        temporary.flush()
                        os.fsync(temporary.fileno())
                    os.replace(temporary_name, path)
                    temporary_name = ""
                    entries = tuple(
                        sorted(
                            (entry for entry in directory.glob("*/*.json") if entry.is_file()),
                            key=lambda entry: (entry.stat().st_mtime_ns, entry.as_posix()),
                        )
                    )
                    sizes = {entry: entry.stat().st_size for entry in entries}
                    total = sum(sizes.values())
                    for entry in entries:
                        if total <= settings.PROJECT_HEALTH_CACHE_MAX_BYTES:
                            break
                        entry.unlink()
                        total -= sizes[entry]
                finally:
                    if temporary_name:
                        Path(temporary_name).unlink(missing_ok=True)
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        except OSError:
            return CacheOutcomeState.UNAVAILABLE
        return CacheOutcomeState.STORED
