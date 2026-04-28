# __sig__: 76a253b5 | build:2026 | dev:609191fb
"""
GreenNova ERP - Django Settings
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-1*tl_8j6o8nr$+4egpx%dh4$d_w=#t(_q*6%el9sktfxp^l&1_'

DEBUG = True

ALLOWED_HOSTS = ['172.20.10.7', '127.0.0.1', 'localhost', '*']


# ==========================================================
# APPLICATIONS
# ==========================================================
INSTALLED_APPS = [
    'import_export',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'users',
    'inventory',
    'attendance',
    'finance',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'greennova_core.urls'

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

WSGI_APPLICATION = 'greennova_core.wsgi.application'


# ==========================================================
# DATABASE — SQLite WAL modu (database is locked önler)
# ==========================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 30,
        },
    }
}


# ==========================================================
# AUTH
# ==========================================================
AUTH_USER_MODEL = 'users.Personel'

# Giriş yapılmamışsa admin login'e yönlendir
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ==========================================================
# I18N
# ==========================================================
LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True


# ==========================================================
# STATIC & MEDIA
# ==========================================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# ==========================================================
# DEFAULTS
# ==========================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Import/Export
IMPORT_EXPORT_SKIP_ADMIN_LOG = True
IMPORT_EXPORT_ENCODING = 'utf-8-sig'

# ==========================================================
# ŞİRKET BİLGİLERİ (PDF belgelerde görünür)
# ==========================================================
COMPANY_NAME = 'GreenNova Tarım Ürünleri'
COMPANY_ADDRESS = 'Bursa / Türkiye'
COMPANY_PHONE = ''
COMPANY_VERGI_NO = ''
COMPANY_VERGI_DAIRESI = ''
