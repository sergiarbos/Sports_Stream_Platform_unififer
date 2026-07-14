"""
Django settings for the SportLink project.

Sensitive values (API keys, SECRET_KEY in production, etc.) are read
from the .env file via django-environ. See README.md and .env.example
to find out which variables you need and which ones are safe to publish
to the GitHub repository.
"""

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
)
# Read the .env file if it exists (local development). In production
# (Render, Railway, PythonAnywhere...) variables are set directly in
# the provider's dashboard — no .env file needed.
environ.Env.read_env(BASE_DIR / ".env")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-sportlink-dev-key")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_huey",
    "schedule",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # i18n: detect language from URL/cookie
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "streamsync.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "streamsync.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
# SQLite by default (zero configuration, perfect for local development).
# If you deploy to a real server, define DATABASE_URL in .env and
# uncomment the line below.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
# DATABASES['default'] = env.db('DATABASE_URL') if env('DATABASE_URL', default=None) else DATABASES['default']


# ---------------------------------------------------------------------------
# Cache — Django Database Cache (SQLite, zero extra dependencies).
# In production with Redis uncomment the redis backend below and set
# CACHE_URL=redis://127.0.0.1:6379/1 in your .env.
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "TIMEOUT": 3600,  # 1-hour default TTL
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        },
    }
}
# Redis alternative (uncomment when available):
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': env('CACHE_URL', default='redis://127.0.0.1:6379/1'),
#     }
# }

# TTL for external API responses (seconds). 1 h by default.
API_CACHE_TTL = env.int("API_CACHE_TTL", default=3600)


# ---------------------------------------------------------------------------
# Huey — Background Task Queue (SQLite backend, no Redis required)
# ---------------------------------------------------------------------------
# django-huey wraps multiple Huey instances; 'default' points to the
# queue name used when no queue= kwarg is specified.

DJANGO_HUEY = {
    "default": "main",
    "queues": {
        "main": {
            "huey_class": "huey.SqliteHuey",
            "name": "sportlink",
            "filename": str(BASE_DIR / "huey.db"),
            "immediate": False,  # set True in tests to run tasks synchronously
            "consumer": {
                "workers": 2,
                "worker_type": "thread",
                "scheduler_interval": 60,
                "verbose": True,
                "logfile": str(BASE_DIR / "huey.log"),
            },
        }
    },
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ---------------------------------------------------------------------------
# Internationalization (i18n)
# ---------------------------------------------------------------------------
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "es"

LANGUAGES = [
    ("es", "Español"),
    ("en", "English"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

TIME_ZONE = "Europe/Madrid"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# External API keys (sports / calendars)
# ---------------------------------------------------------------------------
# Read from .env — NEVER write them directly here.
# See README.md -> "APIs" section to learn which keys are safe to publish
# (not secret, e.g. public demo/free-tier keys) and which must always
# remain private.
API_FOOTBALL_KEY = env("API_FOOTBALL_KEY", default="")
THESPORTSDB_KEY = env("THESPORTSDB_KEY", default="3")  # "3" = public test key
API_TENNIS_KEY = env("API_TENNIS_KEY", default="")
