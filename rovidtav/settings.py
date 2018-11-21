"""
Django settings for rovidtav project.

Generated by 'django-admin startproject' using Django 1.8.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ''

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

ADMIN_LOGIN_REDIRECT_URL = '/admin/rovidtav/ticket/'

IMAGE_DOWNSCALE_PX = 900
IMAGE_THUMB_PX = 180

SELF_URL = 'http://localhost:8000'
SMTP_SERVER = ''
SMTP_USER = ''
SMTP_PASS = ''
EMAIL_SENDER = ''

# Changing this value to a random number or string here will
# force CSS and JS browser cache refresh
CACHE_REFRESH = '534'

# =============================================================================
# JET SETTINGS
# =============================================================================
JET_SIDE_MENU_COMPACT = True
JET_DEFAULT_THEME = 'rovidtav'
JET_CHANGE_FORM_SIBLING_LINKS = False

# Application definition

INSTALLED_APPS = (
    'rovidtav',
    'jet',
    'django_messages',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'model_report',
    'multiselectfield',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',

    'rovidtav.middleware.adminlocale.AdminLocaleMiddleware',
    'rovidtav.middleware.whodidwhat.WhoDidWhat',
    'rovidtav.middleware.preservefilters.PreserveFilters',
)

ROOT_URLCONF = 'rovidtav.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'rovidtav.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'hu-HU'

TIME_ZONE = 'Europe/Budapest'

USE_I18N = True

USE_L10N = True

USE_TZ = True

ADMIN_LANGUAGE_CODE = 'hu-HU'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

try:
    from local_settings import *
except ImportError:
    pass
