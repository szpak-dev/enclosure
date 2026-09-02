from collections.abc import Mapping
from dataclasses import dataclass

from jinja2 import Environment, PackageLoader, StrictUndefined, TemplateError
from wireup import injectable


@injectable
@dataclass(frozen=True)
class TemplateService:
    def render(
        self,
        package: str,
        template: str,
        context: Mapping[str, object],
    ) -> str:
        try:
            environment = Environment(
                loader=PackageLoader(package, "templates"),
                autoescape=False,
                undefined=StrictUndefined,
                extensions=["jinja2.ext.do"],
                keep_trailing_newline=True,
                trim_blocks=True,
                lstrip_blocks=True,
            )
            return environment.get_template(template).render(context)
        except TemplateError as error:
            raise ValueError(f"Could not render template {template} from {package}.") from error
