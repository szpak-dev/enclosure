from markdown_it import MarkdownIt
from wireup import injectable

from ..base import Language, PackageManager, Tool, VersionProvider


@injectable(as_type=Language, qualifier="markdown")
class Markdown(Language):
    id: str = "markdown"
    name: str = "Markdown"
    executable: str = "md"
    requires_extraction: bool = False
    source_extensions: tuple[str, ...] = (".md",)
    aliases: tuple[str, ...] = ()

    def validate(self, path: str, content: str) -> None:
        super().validate(path, content)
        MarkdownIt("commonmark").parse(content)

    package_managers: tuple[PackageManager, ...] = ()
    tools: tuple[Tool, ...] = ()
    stable_version: str = ""
    version_provider: VersionProvider = VersionProvider(
        kind="npm",
        url="https://registry.npmjs.org/mermaid/latest",
        result_path=("version",),
    )
