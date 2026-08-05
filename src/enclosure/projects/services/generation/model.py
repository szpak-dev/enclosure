from pydantic import BaseModel, ConfigDict


class GenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    files: tuple[str, ...]
