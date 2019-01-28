
# minimal django settings required to run tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "test.db",
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'parasol',
)

# Keeping this blank avoids false detections from SECRET_KEY
# repository checkers.
# SECRET_KEY = ''
