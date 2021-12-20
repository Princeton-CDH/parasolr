# minimal django settings required to build documentation
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "test.db",
    }
}

INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "parasolr",
)

SECRET_KEY = "ymY{RQ;P-3NL+?V-Z3P,VJeqbvcF)s.F*MtI?CkB7vAB=AJ&VB"
