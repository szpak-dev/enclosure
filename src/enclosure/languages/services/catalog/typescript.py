from wireup import injectable

from ..base import Language, PackageManager, Tool, VersionProvider


@injectable(as_type=Language, qualifier="typescript")
class Typescript(Language):
    id: str = "typescript"
    name: str = "TypeScript"
    executable: str = "tsc"
    requires_extraction: bool = True
    source_extensions: tuple[str, ...] = (".tsx", ".ts", ".jsx", ".js")
    aliases: tuple[str, ...] = ("ts",)

    def validate(self, path: str, content: str) -> None:
        super().validate(path, content)

    package_managers: tuple[PackageManager, ...] = (
        PackageManager(
            id="npm",
            name="NPM",
            executable="npm",
            manifest_paths=("package.json",),
            lockfile_paths=("package-lock.json",),
            registry_url="https://registry.npmjs.org",
            package_url_type="npm",
            version_constraint="semver",
            supports_workspaces=True,
            commit_lockfiles=True,
            commands={
                "init": "npm init",
                "install": "npm install",
                "add_runtime": "npm install {package}",
                "add_development": "npm install --save-dev {package}",
                "add_optional": "npm install --save-optional {package}",
                "add_peer": "npm install --save-peer {package}",
                "remove": "npm uninstall {package}",
                "update": "npm update",
                "lock": "npm install --package-lock-only",
                "run": "npm run {command}",
                "publish": "npm publish",
                "audit": "npm audit",
            },
        ),
    )
    tools: tuple[Tool, ...] = (
        Tool(
            id="typescript",
            name="TypeScript",
            roles=("type_checker", "build"),
            executable="tsc",
            package_name="typescript",
            stable_version="",
            homepage_url="https://www.typescriptlang.org/",
            config_paths=("tsconfig.json",),
            default_enabled=True,
            commands={"check": "tsc --noEmit", "build": "tsc"},
        ),
        Tool(
            id="eslint",
            name="ESLint",
            roles=("linter",),
            executable="eslint",
            package_name="eslint",
            stable_version="",
            homepage_url="https://eslint.org/",
            config_paths=("eslint.config.js",),
            default_enabled=True,
            commands={"check": "eslint .", "fix": "eslint . --fix"},
        ),
        Tool(
            id="prettier",
            name="Prettier",
            roles=("formatter",),
            executable="prettier",
            package_name="prettier",
            stable_version="",
            homepage_url="https://prettier.io/",
            config_paths=(".prettierrc",),
            default_enabled=True,
            commands={"check": "prettier . --check", "fix": "prettier . --write"},
        ),
        Tool(
            id="vitest",
            name="Vitest",
            roles=("test_runner",),
            executable="vitest",
            package_name="vitest",
            stable_version="",
            homepage_url="https://vitest.dev/",
            config_paths=("vitest.config.ts",),
            default_enabled=True,
            commands={"test": "vitest run", "serve": "vitest"},
        ),
        Tool(
            id="vitest-v8",
            name="Vitest V8",
            roles=("coverage",),
            executable="vitest",
            package_name="@vitest/coverage-v8",
            stable_version="",
            homepage_url="https://vitest.dev/guide/coverage",
            config_paths=("vitest.config.ts",),
            default_enabled=True,
            commands={"coverage": "vitest run --coverage"},
        ),
        Tool(
            id="tsx",
            name="tsx",
            roles=("development_runner",),
            executable="tsx",
            package_name="tsx",
            stable_version="",
            homepage_url="https://tsx.is/",
            config_paths=(),
            default_enabled=True,
            commands={"serve": "tsx watch {entrypoint}"},
        ),
        Tool(
            id="typedoc",
            name="TypeDoc",
            roles=("documentation",),
            executable="typedoc",
            package_name="typedoc",
            stable_version="",
            homepage_url="https://typedoc.org/",
            config_paths=("typedoc.json",),
            default_enabled=False,
            commands={"build": "typedoc"},
        ),
    )
    stable_version: str = ""
    version_provider: VersionProvider = VersionProvider(
        kind="npm",
        url="https://registry.npmjs.org/typescript/latest",
        result_path=("version",),
    )
