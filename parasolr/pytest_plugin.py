import logging

import pytest

try:
    import django
    from django.conf import settings
    from django.test import override_settings
except ImportError:
    django = None

from parasolr import django
from parasolr.schema import SolrSchema


logger = logging.getLogger(__name__)


if django:


    def get_test_solr_config():
        '''Get configuration for test Solr connection based on
        default and test options in django settings. Any test configuration
        options specified are used; if no test collection name
        is specified, generates one based on the configured collection.'''

        # copy default config for basic connection optiosn (e.g. url)
        test_config = settings.SOLR_CONNECTIONS['default'].copy()

        # use test settings as primary: anything in test settings
        # should override default settings
        if 'TEST' in settings.SOLR_CONNECTIONS['default']:
            test_config.update(settings.SOLR_CONNECTIONS['default']['TEST'])

        # if test collection is not explicitly configured,
        # set it based on default collection
        if 'TEST' not in test_config or \
         'COLLECTION' not in settings.SOLR_CONNECTIONS['default']['TEST']:
            test_config['COLLECTION'] = 'test_%s' % \
                settings.SOLR_CONNECTIONS['default']['COLLECTION']

        logger.info('Configuring Solr for tests %(URL)s%(COLLECTION)s',
                    test_config)
        return test_config

    @pytest.fixture(autouse=True, scope="session")
    def configure_django_test_solr():
        """Automatically configure the default Solr to use a test
        core based on the configured **SOLR_CONNECTIONS**.  Will use
        test name if specified (using the same structure as Django
        DATABASES), or prepend "test_" to the configured COLLECTION
        if no test name is set. The test core will be created and
        schema configured before starting, and unloaded after tests
        complete.  Example configuration::

            SOLR_CONNECTIONS = {
                'default': {
                    'URL': 'http://localhost:8983/solr/',
                    'COLLECTION': 'myproj',
                    'TEST': {
                        'NAME': 'testproj',
                        }
                }
            }

        """

        solr_config_opts = get_test_solr_config()

        logger.info('Configuring Solr for tests %(URL)s%(COLLECTION)s',
                    solr_config_opts)

        with override_settings(SOLR_CONNECTIONS={'default': solr_config_opts}):
            # reload core before and after to ensure field list is accurate
            solr = django.SolrClient(commitWithin=10)
            response = solr.core_admin.status(core=solr_config_opts['COLLECTION'])
            if not response.status.get(solr_config_opts['COLLECTION'], None):
                solr.core_admin.create(solr_config_opts['COLLECTION'],
                                       configSet=solr_config_opts.get('CONFIGSET', 'basic_configs'))

            try:
                # if a schema is configured, update the test core
                schema_config = SolrSchema.get_configuration()
                schema_config.configure_fieldtypes(solr)
                schema_config.configure_fields(solr)
            except Exception:
                pass

            # yield settings so tests run with overridden solr connection
            yield settings

            # clear out any data indexed in test collection
            solr.update.delete_by_query('*:*')
            # and unload
            solr.core_admin.unload(
                solr_config_opts['COLLECTION'],
                deleteInstanceDir=True,
                deleteIndex=True,
                deleteDataDir=True
            )
