import os

MAJOR_SOLR_VERSION = int(os.environ.get('SOLR_VERSION', '8').split('.')[0])
configset = 'basic_configs' if MAJOR_SOLR_VERSION < 7 else '_default'

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
    'parasolr',
)

# Keeping this blank avoids false detections from SECRET_KEY
# repository checkers.
# SECRET_KEY = ''


# Default CI test settings; imported by parasol.solr.test_solr as testsettings
# from top level project folder
SOLR_CONNECTIONS = {
    'default': {
        # default config for testing pytest plugin
        'URL': 'http://localhost:8983/solr/',
        'COLLECTION': 'myplugin',
        'CONFIGSET': configset,
        'TEST': {
            'URL': 'http://localhost:8983/solr/',
            'COLLECTION': 'parasolr_test',
            # aggressive commitWithin for test only
            'COMMITWITHIN': 750,
            'CONFIGSET': configset,
            'MAJOR_SOLR_VERSION': MAJOR_SOLR_VERSION
        }
    }
}
