from dataclasses import dataclass, field
from hashlib import sha256

from wireup import injectable


@injectable
@dataclass(frozen=True)
class SafeMetadataRedactor:
    redacted_keys: frozenset[str] = field(
        default=frozenset(
            {
                "authorization",
                "cookie",
                "password",
                "secret",
                "token",
            }
        ),
        init=False,
    )

    def digest(self, payload: bytes) -> str:
        return sha256(payload).hexdigest()

    def redact(self, metadata: dict[str, str]) -> dict[str, str]:
        return {key: "[redacted]" if key.lower() in self.redacted_keys else value for key, value in metadata.items()}
