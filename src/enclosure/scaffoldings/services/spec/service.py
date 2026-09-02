from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue, ValidationError
from wireup import injectable

from enclosure.shared import SourceCodePackage

from ...errors import ScaffoldingError
from .model import PreparedScaffolding, ScaffoldingSpec


@injectable
@dataclass(frozen=True)
class ScaffoldingSpecService:
    def validate(self, value: Mapping[str, object] | ScaffoldingSpec) -> ScaffoldingSpec:
        spec = self._parse(value)
        self._validate_template_content_paths(spec)
        return spec

    def prepare(
        self,
        value: Mapping[str, object] | ScaffoldingSpec,
        parameters: Mapping[str, JsonValue],
    ) -> PreparedScaffolding:
        spec = self.validate(value)
        return PreparedScaffolding(
            spec=spec,
            source=self._source(spec),
            parameters=self._validate_parameters(spec, parameters),
        )

    def _parse(self, value: Mapping[str, object] | ScaffoldingSpec) -> ScaffoldingSpec:
        if isinstance(value, ScaffoldingSpec):
            return value
        try:
            return ScaffoldingSpec.model_validate(value)
        except ValidationError as error:
            raise ScaffoldingError(str(error)) from error

    def _source(self, spec: ScaffoldingSpec) -> SourceCodePackage:
        return SourceCodePackage(
            language=spec.language,
            package={"files": {template.path: template.content for template in spec.templates}},
        )

    @staticmethod
    def _validate_template_content_paths(spec: ScaffoldingSpec) -> None:
        for template in spec.templates:
            if not template.path.endswith(".jinja") and any(token in template.content for token in ("{{", "{%", "{#")):
                raise ScaffoldingError("Template content uses Jinja syntax; its path must end with '.jinja'.")

    def _validate_parameters(
        self,
        spec: ScaffoldingSpec,
        parameters: Mapping[str, JsonValue],
    ) -> dict[str, JsonValue]:
        variables = {variable.name: variable for variable in spec.variables}
        supplied = set(parameters)
        missing = variables.keys() - supplied
        unexpected = supplied - variables.keys()

        if missing or unexpected:
            details = []
            if missing:
                details.append(f"missing: {', '.join(sorted(missing))}")
            if unexpected:
                details.append(f"unexpected: {', '.join(sorted(unexpected))}")
            raise ScaffoldingError(f"Invalid rendering parameters ({'; '.join(details)}).")

        try:
            return {name: variable.validate_value(parameters[name]) for name, variable in variables.items()}
        except ValidationError as error:
            raise ScaffoldingError(str(error)) from error
