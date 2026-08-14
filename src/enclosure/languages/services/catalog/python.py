from wireup import injectable

from ..base import Language, PackageManager, Tool, VersionProvider


@injectable(as_type=Language, qualifier="python")
class Python(Language):
    id: str = "python"
    name: str = "Python"
    executable: str = "python"
    requires_extraction: bool = True
    source_extensions: tuple[str, ...] = (".py",)
    aliases: tuple[str, ...] = ("py",)

    def validate(self, path: str, content: str) -> None:
        super().validate(path, content)

    package_managers: tuple[PackageManager, ...] = (
        PackageManager(
            id="uv",
            name="UV",
            executable="uv",
            manifest_paths=("pyproject.toml",),
            lockfile_paths=("uv.lock",),
            registry_url="https://pypi.org/simple",
            package_url_type="pypi",
            version_constraint="pep440",
            supports_workspaces=True,
            commit_lockfiles=True,
            commands={
                "init": "uv init",
                "install": "uv sync",
                "add_runtime": "uv add {package}",
                "add_development": "uv add --dev {package}",
                "add_optional": "uv add --optional {group} {package}",
                "remove": "uv remove {package}",
                "update": "uv lock --upgrade",
                "lock": "uv lock",
                "run": "uv run {command}",
                "publish": "uv publish",
            },
        ),
    )
    tools: tuple[Tool, ...] = (
        Tool(
            id="ruff",
            name="Ruff",
            roles=("formatter", "linter"),
            executable="ruff",
            package_name="ruff",
            stable_version="",
            homepage_url="https://docs.astral.sh/ruff/",
            config_paths=(),
            default_enabled=True,
            commands={
                "check": "ruff check . && ruff format --check .",
                "fix": "ruff check --fix . && ruff format .",
            },
        ),
        Tool(
            id="basedpyright",
            name="basedpyright",
            roles=("type_checker",),
            executable="basedpyright",
            package_name="basedpyright",
            stable_version="",
            homepage_url="https://docs.basedpyright.com/",
            config_paths=("pyrightconfig.json",),
            default_enabled=True,
            commands={"check": "basedpyright"},
        ),
        Tool(
            id="pytest",
            name="pytest",
            roles=("test_runner",),
            executable="pytest",
            package_name="pytest",
            stable_version="",
            homepage_url="https://docs.pytest.org/",
            config_paths=("pyproject.toml",),
            default_enabled=True,
            commands={"test": "pytest"},
        ),
        Tool(
            id="coverage",
            name="coverage.py",
            roles=("coverage",),
            executable="coverage",
            package_name="coverage",
            stable_version="",
            homepage_url="https://coverage.readthedocs.io/",
            config_paths=(".coveragerc", "pyproject.toml"),
            default_enabled=True,
            commands={"coverage": "coverage run -m pytest && coverage report"},
        ),
        Tool(
            id="build",
            name="build",
            roles=("build",),
            executable="python",
            package_name="build",
            stable_version="",
            homepage_url="https://build.pypa.io/",
            config_paths=("pyproject.toml",),
            default_enabled=True,
            commands={"build": "python -m build"},
        ),
        Tool(
            id="mkdocs",
            name="MkDocs",
            roles=("documentation",),
            executable="mkdocs",
            package_name="mkdocs",
            stable_version="",
            homepage_url="https://www.mkdocs.org/",
            config_paths=("mkdocs.yml",),
            default_enabled=False,
            commands={"build": "mkdocs build", "serve": "mkdocs serve"},
        ),
    )
    stable_version: str = ""
    version_provider: VersionProvider = VersionProvider(
        kind="endoflife",
        url="https://endoflife.date/api/python.json",
        result_path=(0, "latest"),
    )
