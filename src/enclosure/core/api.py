from importlib import import_module

from django.apps import apps
from django.utils.module_loading import module_has_submodule
from modwire_hex.django import DjangoNinja
from ninja_extra.controllers.registry import controller_registry

from .controllers import RootController
from .error_handling import ExceptionHandlers

api = DjangoNinja.api()
ExceptionHandlers().configure(api)
api.register_controllers(RootController)

for app_config in apps.get_app_configs():
    if not app_config.name.startswith("enclosure."):
        continue
    app_module = import_module(app_config.name)
    if not module_has_submodule(app_module, "api"):
        continue
    api_module = import_module(f"{app_config.name}.api")
    if module_has_submodule(api_module, "controllers"):
        import_module(f"{app_config.name}.api.controllers")

api.register_controllers(*controller_registry.get_controllers().values())
openapi_schema = api.get_openapi_schema(path_prefix="/api")
