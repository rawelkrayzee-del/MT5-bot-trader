"""
Django settings for MT5 Trading Bot project.

This file contains configuration for a comprehensive full-stack
MetaTrader 5 trading bot platform with real-time capabilities,
advanced analytics, and modern web interface.
"""

import os
import environ
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    USE_POSTGRES=(bool, True),
    USE_REDIS=(bool, True),
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-mt5-trading-bot-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# CSRF Settings for production
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://*.defang.dev'
])

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'django_extensions',
    'channels',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django_celery_beat',
    'django_celery_results',
]

LOCAL_APPS = [
    'accounts',
    'trading',
    'strategies',
    'analytics',
    'mt5_integration',
    'websocket_app',
    'risk_management',
    'market_data',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Development apps
if DEBUG:
    INSTALLED_APPS += [
        'debug_toolbar',
        'silk',
    ]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# Development middleware
if DEBUG:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    MIDDLEWARE.insert(1, 'silk.middleware.SilkyMiddleware')

ROOT_URLCONF = 'defang_sample.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'defang_sample.wsgi.application'
ASGI_APPLICATION = 'defang_sample.asgi.application'

# Database configuration
if env('USE_POSTGRES'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='mt5_trading_db'),
            'USER': env('DB_USER', default='postgres'),
            'PASSWORD': env('DB_PASSWORD', default='postgres'),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
            'OPTIONS': {
                'MAX_CONNS': 20,
                'CONN_MAX_AGE': 600,
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Cache configuration
if env('USE_REDIS'):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
    
    # Session backend
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Channel layers for WebSocket
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL', default='redis://localhost:6379/0')],
        },
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Django REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': env('JWT_SECRET_KEY', default=SECRET_KEY),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS settings
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
])

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only for development

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

# Celery Beat Schedule
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# WhiteNoise configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Site ID for allauth
SITE_ID = 1

# Email configuration (for development)
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = env('EMAIL_HOST', default='localhost')
    EMAIL_PORT = env('EMAIL_PORT', default=587)
    EMAIL_USE_TLS = env('EMAIL_USE_TLS', default=True)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'trading': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'mt5_integration': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Create logs directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

# MT5 Trading Bot Specific Settings
MT5_SETTINGS = {
    'CONNECTION': {
        'LOGIN': env('MT5_LOGIN', default=''),
        'PASSWORD': env('MT5_PASSWORD', default=''),
        'SERVER': env('MT5_SERVER', default='MetaQuotes-Demo'),
        'PATH': env('MT5_PATH', default=''),
        'TIMEOUT': env('MT5_TIMEOUT', default=60000),
        'PORTABLE': env('MT5_PORTABLE', default=False),
    },
    'TRADING': {
        'DEFAULT_RISK_PERCENT': env('DEFAULT_RISK_PERCENT', default=1.0),
        'MAX_RISK_PERCENT': env('MAX_RISK_PERCENT', default=5.0),
        'DEFAULT_SLIPPAGE': env('DEFAULT_SLIPPAGE', default=3),
        'MAX_SPREAD': env('MAX_SPREAD', default=5),
        'MAGIC_NUMBER': env('MAGIC_NUMBER', default=123456),
        'ENABLE_LIVE_TRADING': env('ENABLE_LIVE_TRADING', default=False),
    },
    'RISK_MANAGEMENT': {
        'MAX_DRAWDOWN_PERCENT': env('MAX_DRAWDOWN_PERCENT', default=10.0),
        'MAX_DAILY_LOSS_PERCENT': env('MAX_DAILY_LOSS_PERCENT', default=3.0),
        'MAX_POSITIONS': env('MAX_POSITIONS', default=10),
        'CORRELATION_LIMIT': env('CORRELATION_LIMIT', default=0.7),
    },
    'DATA': {
        'UPDATE_INTERVAL_SECONDS': env('DATA_UPDATE_INTERVAL', default=1),
        'HISTORY_DAYS': env('HISTORY_DAYS', default=30),
        'CACHE_DURATION_SECONDS': env('CACHE_DURATION', default=300),
    },
    'NOTIFICATIONS': {
        'ENABLE_EMAIL': env('ENABLE_EMAIL_NOTIFICATIONS', default=False),
        'ENABLE_WEBHOOK': env('ENABLE_WEBHOOK_NOTIFICATIONS', default=False),
        'WEBHOOK_URL': env('WEBHOOK_URL', default=''),
        'EMAIL_RECIPIENTS': env.list('EMAIL_RECIPIENTS', default=[]),
    }
}

# External API Keys
API_KEYS = {
    'ALPHA_VANTAGE': env('ALPHA_VANTAGE_API_KEY', default=''),
    'FINANCIAL_MODELING_PREP': env('FINANCIAL_MODELING_PREP_API_KEY', default=''),
    'TWELVE_DATA': env('TWELVE_DATA_API_KEY', default=''),
    'TRADINGVIEW': env('TRADINGVIEW_API_KEY', default=''),
}

# Trading Hours Configuration
TRADING_HOURS = {
    'FOREX': {
        'MONDAY': {'start': '22:00', 'end': '22:00'},  # Sunday 22:00 to Friday 22:00 UTC
        'TUESDAY': {'start': '00:00', 'end': '23:59'},
        'WEDNESDAY': {'start': '00:00', 'end': '23:59'},
        'THURSDAY': {'start': '00:00', 'end': '23:59'},
        'FRIDAY': {'start': '00:00', 'end': '22:00'},
    },
    'STOCKS': {
        'MONDAY': {'start': '14:30', 'end': '21:00'},  # NYSE hours in UTC
        'TUESDAY': {'start': '14:30', 'end': '21:00'},
        'WEDNESDAY': {'start': '14:30', 'end': '21:00'},
        'THURSDAY': {'start': '14:30', 'end': '21:00'},
        'FRIDAY': {'start': '14:30', 'end': '21:00'},
    }
}

# Strategy Configuration
STRATEGY_SETTINGS = {
    'MAX_STRATEGIES_PER_USER': env('MAX_STRATEGIES_PER_USER', default=10),
    'BACKTEST_MAX_DAYS': env('BACKTEST_MAX_DAYS', default=365),
    'OPTIMIZATION_MAX_ITERATIONS': env('OPTIMIZATION_MAX_ITERATIONS', default=1000),
    'ENABLE_PAPER_TRADING': env('ENABLE_PAPER_TRADING', default=True),
}

# Development settings
if DEBUG:
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]
    
    # Debug toolbar panels
    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
    ]
