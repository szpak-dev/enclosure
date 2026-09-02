from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any

import wireup
from django.conf import settings
from modwire_hex import DjangoApplication

_package_root = Path(__file__).parent
_package_name = __package__
_installed_apps = {app.partition(".apps.")[0] for app in settings.INSTALLED_APPS if app.startswith(f"{_package_name}.")}
_package_paths = sorted(
    {
        path
        for pattern in ("shared", "*/shared", "*/services")
        for path in _package_root.glob(pattern)
        if (path / "__init__.py").is_file()
        and (
            path == _package_root / "shared"
            or f"{_package_name}.{path.parent.relative_to(_package_root).as_posix().replace('/', '.')}"
            in _installed_apps
        )
    }
)
_injectables: list[ModuleType] = [
    import_module(f"{_package_name}.{package.relative_to(_package_root).as_posix().replace('/', '.')}")
    for package in _package_paths
]


class AutowiredDjangoApplication(DjangoApplication):
    def create_container(self) -> Any:
        return wireup.create_sync_container(injectables=_injectables)


application = AutowiredDjangoApplication(modules=())
