import fcntl
from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True)
class HealthSlotLease:
    slot_index: int
    handle: BinaryIO

    def release(self) -> None:
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()
