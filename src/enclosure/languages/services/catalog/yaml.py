import yaml
from wireup import injectable

from ..base import Language, PackageManager, Tool, VersionProvider
from ..errors import LanguagesError


@injectable(as_type=Language, qualifier="yaml")
class Yaml(Language):
    id: str = "yaml"
    name: str = "Yaml"
    executable: str = "yml"
    requires_extraction: bool = False
    source_extensions: tuple[str, ...] = (".yml", ".yaml",)
    aliases: tuple[str, ...] = ()

    def validate(self, path: str, content: str) -> None:
        super().validate(path, content)
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as error:
            raise LanguagesError(f"Invalid YAML content: {error}") from error

    package_managers: tuple[PackageManager, ...] = ()
    tools: tuple[Tool, ...] = ()
    stable_version: str = ""
    version_provider: VersionProvider = VersionProvider(
        kind="npm",
        url="https://registry.npmjs.org/mermaid/latest",
        result_path=("version",),
    )
