from django.conf import settings
from django.views.generic import TemplateView


class BrowserIndexView(TemplateView):
    template_name = "browser/index.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        context["siren_root"] = getattr(settings, "SIRENITY_ROOT", "/siren/")
        return context
