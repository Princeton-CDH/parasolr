import logging

import pytest

try:
    import django
    from django.conf import settings
    from django.test import override_settings
except ImportError:
    django = None

from parasol import django
from parasol.schema import SolrSchema


logger = logging.getLogger(__name__)


if django:

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

        if 'TEST' in settings.SOLR_CONNECTIONS['default'] and \
          'NAME' in settings.SOLR_CONNECTIONS['default']['TEST']:
            test_collection = settings.SOLR_CONNECTIONS['default']['TEST']['NAME']
        else:
            test_collection = 'test_%s'% settings.SOLR_CONNECTIONS['default']['COLLECTION']

        test_config = settings.SOLR_CONNECTIONS['default'].copy()
        test_config['COLLECTION'] = test_collection

        logger.info('Configuring Solr for tests %s%s',
                    test_config['URL'], test_collection)

        with override_settings(SOLR_CONNECTIONS={'default': test_config}):
            # reload core before and after to ensure field list is accurate
            solr = django.SolrClient(commitWithin=10)
            response = solr.core_admin.status(core=test_collection)
            if not response.status.get(test_collection, None):
                solr.core_admin.create(test_collection, configSet='basic_configs')

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
                test_collection,
                deleteInstanceDir=True,
                deleteIndex=True,
                deleteDataDir=True
            )
