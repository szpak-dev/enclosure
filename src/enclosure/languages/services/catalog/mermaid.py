from wireup import injectable

from ..base import Language, PackageManager, Tool, VersionProvider


@injectable(as_type=Language, qualifier="mermaid")
class Mermaid(Language):
    id: str = "mermaid"
    name: str = "Mermaid"
    executable: str = "mmdc"
    requires_extraction: bool = False
    source_extensions: tuple[str, ...] = (".mermaid", ".mmd")
    aliases: tuple[str, ...] = ()

    def validate(self, path: str, content: str) -> None:
        super().validate(path, content)

    package_managers: tuple[PackageManager, ...] = ()
    tools: tuple[Tool, ...] = (
        Tool(
            id="mermaid-cli",
            name="Mermaid CLI",
            roles=("diagram_renderer", "diagram_validator"),
            executable="mmdc",
            package_name="@mermaid-js/mermaid-cli",
            stable_version="",
            homepage_url="https://mermaid.js.org/",
            config_paths=("mermaid.config.json",),
            default_enabled=True,
            commands={"render": "mmdc -i {input} -o {output}"},
        ),
    )
    stable_version: str = ""
    version_provider: VersionProvider = VersionProvider(
        kind="npm",
        url="https://registry.npmjs.org/mermaid/latest",
        result_path=("version",),
    )
