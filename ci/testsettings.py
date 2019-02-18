
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


# Default CI test settings; imported by parasol.solr.test_solr as testsettings
# from top level project folder
SOLR_CONNECTIONS = {
    'default': {
        'TEST': {
            'URL': 'http://localhost:8983/solr/',
            'COLLECTION': 'parasol_test',
            # aggressive commitWithin for test only
            'COMMITWITHIN': 750,
            'CONFIGSET': 'basic_configs'
        }
    }
}