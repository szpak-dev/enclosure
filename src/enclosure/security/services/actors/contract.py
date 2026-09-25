from abc import ABC, abstractmethod

from .model import Actor


class BearerIdentityProvider(ABC):
    @abstractmethod
    def authenticate(self, token: str) -> Actor:
        raise NotImplementedError

    @abstractmethod
    def issue(self, actor: Actor) -> str:
        raise NotImplementedError
