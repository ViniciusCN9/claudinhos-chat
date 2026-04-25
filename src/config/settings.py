from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"

load_dotenv(ROOT_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


def _build_model_catalog() -> list[dict[str, str]]:
    local_model = os.getenv("OLLAMA_LOCAL_MODEL", "gemma3:1b").strip() or "gemma3:1b"
    cloud_model = os.getenv("OLLAMA_CLOUD_MODEL", "gemma4:31b-cloud").strip() or "gemma4:31b-cloud"

    return [
        {
            "name": local_model,
            "label": "Local",
            "execution": "local",
            "api_model": local_model,
        },
        {
            "name": cloud_model,
            "label": "Cloud",
            "execution": "cloud",
            "api_model": cloud_model.removesuffix("-cloud"),
        },
    ]


def _database_config() -> dict[str, object]:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        engine_map = {
            "postgres": "django.db.backends.postgresql",
            "postgresql": "django.db.backends.postgresql",
        }
        return {
            "ENGINE": engine_map.get(parsed.scheme, "django.db.backends.postgresql"),
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": parsed.port or "",
        }

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME", "claudinhos_chat"),
        "USER": os.getenv("DATABASE_USER", "postgres"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", "postgres"),
        "HOST": os.getenv("DATABASE_HOST", "127.0.0.1"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
    }


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "key")
DEBUG = _env_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [SRC_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": _database_config(),
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [SRC_DIR / "static", ROOT_DIR / "assets"]
STATIC_ROOT = ROOT_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_CLOUD_BASE_URL = os.getenv("OLLAMA_CLOUD_BASE_URL", "https://ollama.com").rstrip("/")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "").strip()
OLLAMA_LOCAL_MODEL_KEEP_ALIVE = os.getenv("OLLAMA_LOCAL_MODEL_KEEP_ALIVE", "15m")
OLLAMA_MODEL_CATALOG = _build_model_catalog()
OLLAMA_AVAILABLE_MODELS = [model["name"] for model in OLLAMA_MODEL_CATALOG]
OLLAMA_DEFAULT_MODEL = os.getenv(
    "OLLAMA_DEFAULT_MODEL",
    OLLAMA_AVAILABLE_MODELS[0] if OLLAMA_AVAILABLE_MODELS else "gemma3:1b",
)
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
CHAT_CONTEXT_LIMIT_TOKENS = int(os.getenv("CHAT_CONTEXT_LIMIT_TOKENS", "16384"))
CHAT_DEFAULT_SYSTEM_PROMPT = os.getenv(
    "CHAT_DEFAULT_SYSTEM_PROMPT",
    "Voce e uma inteligencia artificial para responder questionamentos em geral. Voce tem um grande senso de humor e gosta de fazer analogias usando seus colegas como exemplo. Os principais nomes sao Erick, Gui, Vini e Leo. Sempre que possivel, crie parodias sobre o Erick e use jargoes com ditados populares.",
)