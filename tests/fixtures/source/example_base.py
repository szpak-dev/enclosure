from abc import ABC, abstractmethod

class ExampleBase(ABC):
    @abstractmethod
    def execute(self) -> None:
        raise NotImplementedError
