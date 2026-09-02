from abc import ABC, abstractmethod


class BootstrapRepository(ABC):
    @abstractmethod
    def read(self) -> str:
        raise NotImplementedError
