from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-lms-key-xyz-change-in-production'
DEBUG      = True

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'uncontagiously-nonplanetary-aleisha.ngrok-free.dev',
]

CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
    'https://uncontagiously-nonplanetary-aleisha.ngrok-free.dev',
]

CSRF_COOKIE_SAMESITE    = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Google OAuth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # EduLMS apps
    'accounts',
    'courses',
    'teacher',
    'student',
    'assessments',
    'core',
    'superadmin',
    'maintenance',
    # API
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'api',
]

SITE_ID = 1

# ─── DJANGO REST FRAMEWORK ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',
        'user': '120/minute',
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.MaintenanceModeMiddleware',
    'core.middleware.SiteBannerMiddleware',
    'core.middleware.ErrorDetectionMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'lms_project.urls'

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
                'accounts.context_processors.pending_approvals',
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'lms_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME':   BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# ─── GOOGLE OAUTH (allauth) ────────────────────────────────────────────────────
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': '',        # ← set in local_settings.py
            'secret':    '',        # ← set in local_settings.py
            'key':       '',
        }
    }
}
SOCIALACCOUNT_AUTO_SIGNUP      = False   # Show confirm page before creating account
SOCIALACCOUNT_LOGIN_ON_GET     = True
ACCOUNT_EMAIL_VERIFICATION     = 'none'
ACCOUNT_LOGIN_METHODS          = {'username', 'email'}

# ─── JITSI MEET ───────────────────────────────────────────────────────────────
JITSI_DOMAIN  = 'meet.jit.si'           # Free public Jitsi server
JITSI_APP_ID  = ''                       # Optional: your 8x8.vc AppID for private rooms

LOGIN_URL           = '/accounts/login/'
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Manila'
USE_I18N      = True
USE_TZ        = True

STATIC_URL       = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT      = BASE_DIR / 'staticfiles'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── REST FRAMEWORK ────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {'anon':'60/hour','user':'300/hour'},
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':    timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME':   timedelta(days=30),
    'ROTATE_REFRESH_TOKENS':    True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES':        ('Bearer',),
}

# ─── CORS ──────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000','http://localhost:8080',
    'http://127.0.0.1:3000','http://127.0.0.1:8080',
    'capacitor://localhost','ionic://localhost',
]
CORS_ALLOW_CREDENTIALS = True

# ─── SITE URL (for password setup links in emails) ────────────────────────────
# Update this to your ngrok URL while developing, or your domain in production
SITE_BASE_URL = 'https://uncontagiously-nonplanetary-aleisha.ngrok-free.dev/'
SCHOOL_NAME = 'EduLMS'

# ── EMAIL (GMAIL SMTP) ───────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = 'edulmsadmin@gmail.com'
EMAIL_HOST_PASSWORD = 'ydjqgbcmulzfdets'  # Gmail App Password

DEFAULT_FROM_EMAIL = 'EduLMS <edulmsadmin@gmail.com>'
 
# ─── LOGGING ──────────────────────────────────────────────────────────────────
logs_dir = BASE_DIR / 'logs'
logs_dir.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'file':    {'level':'ERROR','class':'logging.FileHandler','filename': logs_dir / 'errors.log','formatter':'verbose'},
        'console': {'class':'logging.StreamHandler','formatter':'verbose'},
    },
    'loggers': {
        'edulms': {'handlers':['file','console'],'level':'DEBUG','propagate':False},
        'django': {'handlers':['file','console'],'level':'ERROR','propagate':False},
    },
}

# ─── LOCAL OVERRIDE (put EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, SITE_BASE_URL here) ──
# Copy local_settings.example.py → local_settings.py and fill in credentials
try:
    from lms_project.local_settings import *  # noqa
except ImportError:
    pass
