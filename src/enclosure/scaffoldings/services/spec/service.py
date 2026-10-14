from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from enclosure.shared.source_code.package import CodePackage, SourceCodePackage

from ...errors import ScaffoldingError
from .model import PreparedScaffolding, ScaffoldingSpec


@injectable
@dataclass(frozen=True)
class ScaffoldingSpecService:
    def prepare(
        self,
        spec: ScaffoldingSpec,
        parameters: dict[str, JsonValue],
    ) -> PreparedScaffolding:
        variables = {variable.name: variable for variable in spec.variables}
        supplied_names = set(parameters)
        missing_names = variables.keys() - supplied_names
        unexpected_names = supplied_names - variables.keys()

        if missing_names or unexpected_names:
            details: list[str] = []
            if missing_names:
                details.append(f"missing: {', '.join(sorted(missing_names))}")
            if unexpected_names:
                details.append(f"unexpected: {', '.join(sorted(unexpected_names))}")
            raise ScaffoldingError(f"Invalid rendering parameters ({'; '.join(details)}).")

        validated_parameters = {name: variable.validate_value(parameters[name]) for name, variable in variables.items()}
        source = SourceCodePackage.model_construct(
            language=spec.language,
            package=CodePackage.model_construct(files={template.path: template.content for template in spec.templates}),
        )
        return PreparedScaffolding(
            spec=spec,
            source=source,
            parameters=validated_parameters,
        )
