import os
from pathlib import Path

import dj_database_url
import structlog
from corsheaders.defaults import default_headers, default_methods
from dotenv import load_dotenv

load_dotenv()


PACKAGE_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PACKAGE_DIR.parent.parent
APPS_DIR = PACKAGE_DIR / "apps"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DEBUG", "0") == "1"
ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1", "testserver"}
LOCAL_DEVELOPMENT = DEBUG or bool(ALLOWED_HOSTS) and all(host in LOCAL_HOSTS for host in ALLOWED_HOSTS)
RELEASE_VERSION = os.getenv("ENCLOSURE_RUNTIME_VERSION", "0.0.0+dev")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "health_check",
    "ninja_extra",
    "pgvector.django",
    "modwire_hex.django.apps.ModwireConfig",
    "enclosure.browser.adapters.http.apps.BrowserHttpConfig",
    "enclosure.diagrams.apps.DiagramsConfig",
    "enclosure.languages.apps.LanguagesConfig",
    "enclosure.scaffoldings.apps.ScaffoldingsDjangoConfig",
    "enclosure.records.apps.RecordsConfig",
    "enclosure.projects.apps.ProjectsConfig",
]

MIDDLEWARE = [
    "modwire_hex.django.middleware.RequestScopeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.http.ConditionalGetMiddleware",
    "sirenity.SirenMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if LOCAL_DEVELOPMENT:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_HEADERS = [*default_headers, "x-actor-id", "x-actor-type"]
    CORS_ALLOW_METHODS = list(default_methods)
MODWIRE = {
    "APPLICATION": "enclosure.autowiring.application",
    "NINJA": {"title": "Enclosure API", "version": RELEASE_VERSION},
}
SIRENITY = {
    "OPENAPI": "enclosure.core.api.api",
    "POLICY": "sirenity.SirenAllowAllPolicy",
    "SOURCE_PATH": "/api",
    "PUBLIC_PATH": "/siren",
    "PROFILES": [
        "sirenity.SirenStructuredFormProfile",
        "enclosure.core.siren.EnclosureRelationshipsProfile",
    ],
}
SIRENITY_ROOT = "/siren/"
ROOT_URLCONF = "enclosure.core.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
ASGI_APPLICATION = "enclosure.core.asgi.application"
WSGI_APPLICATION = "enclosure.core.wsgi.application"
database = dj_database_url.config(default=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"))
if database_host := os.getenv("DATABASE_HOST"):
    database["HOST"] = database_host
if database_port := os.getenv("DATABASE_PORT"):
    database["PORT"] = database_port
DATABASES = {"default": database}
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / ".dev" / "static"
STATICFILES_DIRS = []
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
RECORDS_EMBEDDING_DIMENSIONS = 384
RECORDS_EMBEDDINGS_ENABLED = os.getenv("RECORDS_EMBEDDINGS_ENABLED", "1") == "1"
RECORDS_EMBEDDING_PROVIDER = os.getenv("RECORDS_EMBEDDING_PROVIDER", "deterministic")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processor": structlog.processors.JSONRenderer(),
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
