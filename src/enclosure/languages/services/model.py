from dataclasses import dataclass
from typing import Literal, Protocol

from .errors import LanguagesError

PackageManagerCommand = Literal[
    "init",
    "install",
    "add_runtime",
    "add_development",
    "add_optional",
    "add_peer",
    "remove",
    "update",
    "lock",
    "run",
    "publish",
    "audit",
]
ToolCommand = Literal[
    "init",
    "check",
    "fix",
    "test",
    "coverage",
    "build",
    "serve",
    "audit",
    "render",
]
ToolRole = Literal[
    "build",
    "coverage",
    "development_runner",
    "diagram_renderer",
    "diagram_validator",
    "documentation",
    "formatter",
    "linter",
    "security",
    "test_runner",
    "type_checker",
]
VersionProviderKind = Literal["endoflife", "npm"]
VersionPathItem = str | int


@dataclass(frozen=True)
class VersionProvider:
    kind: VersionProviderKind
    url: str
    result_path: tuple[VersionPathItem, ...]


@dataclass(frozen=True)
class PackageManager:
    id: str
    name: str
    executable: str
    manifest_paths: tuple[str, ...]
    lockfile_paths: tuple[str, ...]
    registry_url: str
    package_url_type: str
    version_constraint: str
    supports_workspaces: bool
    commit_lockfiles: bool
    commands: dict[PackageManagerCommand, str]


@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    roles: tuple[ToolRole, ...]
    executable: str
    package_name: str
    stable_version: str
    homepage_url: str
    config_paths: tuple[str, ...]
    default_enabled: bool
    commands: dict[ToolCommand, str]


class Language(Protocol):
    id: str
    name: str
    executable: str
    requires_extraction: bool
    source_extensions: tuple[str, ...]
    aliases: tuple[str, ...]
    package_managers: tuple[PackageManager, ...]
    tools: tuple[Tool, ...]
    stable_version: str
    version_provider: VersionProvider

    def validate(self, path: str, content: str) -> None:
        if any(part in {".", ".."} for part in path.split("/")):
            raise LanguagesError(f"Invalid source path: {path!r}")
