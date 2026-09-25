from contextvars import ContextVar, Token
from dataclasses import dataclass, field

from wireup import injectable

from .model import Actor


@injectable
@dataclass(frozen=True)
class ActorExecutionContext:
    actors: ContextVar[Actor] = field(default_factory=lambda: ContextVar("enclosure_actor"), init=False)

    def bind(self, actor: Actor) -> Token[Actor]:
        return self.actors.set(actor)

    def current(self) -> Actor:
        return self.actors.get()

    def reset(self, token: Token[Actor]) -> None:
        self.actors.reset(token)
