from pathlib import PurePosixPath

from wireup import injectable

from ..base import Language, PackageManager, Tool, VersionProvider
from ..errors import LanguagesError


@injectable(as_type=Language, qualifier="php")
class PHP(Language):
    id: str = "php"
    name: str = "PHP"
    executable: str = "php"
    requires_extraction: bool = True
    source_extensions: tuple[str, ...] = (".php",)
    aliases: tuple[str, ...] = ()

    def validate(self, path: str, content: str) -> None:
        super().validate(path, content)
        if not path or "\\" in path or PurePosixPath(path).is_absolute():
            raise LanguagesError(f"Invalid PHP namespace path: {path!r}")

    package_managers: tuple[PackageManager, ...] = (
        PackageManager(
            id="composer",
            name="Composer",
            executable="composer",
            manifest_paths=("composer.json",),
            lockfile_paths=("composer.lock",),
            registry_url="https://repo.packagist.org",
            package_url_type="composer",
            version_constraint="composer",
            supports_workspaces=False,
            commit_lockfiles=True,
            commands={
                "init": "composer init",
                "install": "composer install",
                "add_runtime": "composer require {package}",
                "add_development": "composer require --dev {package}",
                "remove": "composer remove {package}",
                "update": "composer update",
                "lock": "composer update --lock",
                "run": "composer run {command}",
                "audit": "composer audit",
            },
        ),
    )
    tools: tuple[Tool, ...] = (
        Tool(
            id="php-cs-fixer",
            name="PHP-CS-Fixer",
            roles=("formatter",),
            executable="php-cs-fixer",
            package_name="friendsofphp/php-cs-fixer",
            stable_version="",
            homepage_url="https://cs.symfony.com/",
            config_paths=(".php-cs-fixer.php",),
            default_enabled=True,
            commands={"check": "php-cs-fixer fix --dry-run --diff",
                      "fix": "php-cs-fixer fix"},
        ),
        Tool(
            id="phpstan",
            name="PHPStan",
            roles=("type_checker",),
            executable="phpstan",
            package_name="phpstan/phpstan",
            stable_version="",
            homepage_url="https://phpstan.org/",
            config_paths=("phpstan.neon",),
            default_enabled=True,
            commands={"check": "phpstan analyse"},
        ),
        Tool(
            id="phpunit",
            name="PHPUnit",
            roles=("test_runner",),
            executable="phpunit",
            package_name="phpunit/phpunit",
            stable_version="",
            homepage_url="https://phpunit.de/",
            config_paths=("phpunit.xml",),
            default_enabled=True,
            commands={"test": "phpunit"},
        ),
        Tool(
            id="xdebug",
            name="Xdebug",
            roles=("coverage",),
            executable="php",
            package_name="ext-xdebug",
            stable_version="",
            homepage_url="https://xdebug.org/",
            config_paths=("phpunit.xml",),
            default_enabled=False,
            commands={"coverage": "XDEBUG_MODE=coverage phpunit --coverage-text"},
        ),
        Tool(
            id="composer-audit",
            name="Composer Audit",
            roles=("security",),
            executable="composer",
            package_name="composer",
            stable_version="",
            homepage_url="https://getcomposer.org/doc/03-cli.md#audit",
            config_paths=(),
            default_enabled=True,
            commands={"audit": "composer audit"},
        ),
    )
    stable_version: str = ""
    version_provider: VersionProvider = VersionProvider(
        kind="endoflife",
        url="https://endoflife.date/api/php.json",
        result_path=(0, "latest"),
    )
