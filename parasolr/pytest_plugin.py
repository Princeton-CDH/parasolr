import logging
from time import sleep
from unittest.mock import MagicMock, Mock

import pytest

try:
    import django
    from django.apps import apps
    from django.conf import settings
    from django.test import override_settings
except ImportError:
    django = None

import parasolr.django as parasolr_django
from parasolr.query.queryset import SolrQuerySet
from parasolr.schema import SolrSchema

logger = logging.getLogger(__name__)


# NOTE: pytest plugins must be conditionally defined to avoid errors
# (requires_django decorator does not work)
if django:

    def get_test_solr_config():
        """Get configuration for test Solr connection based on
        default and test options in django settings. Any test configuration
        options specified are used; if no test collection name
        is specified, generates one based on the configured collection."""

        # skip if parasolr is not actually in django installed apps
        if not apps.is_installed("parasolr"):
            return

        # if no solr connection is configured, bail out
        if not getattr(settings, "SOLR_CONNECTIONS", None):
            logger.warning("No Solr configuration found")
            return

        # copy default config for basic connection options (e.g. url)
        test_config = settings.SOLR_CONNECTIONS["default"].copy()

        # use test settings as primary: anything in test settings
        # should override default settings
        if "TEST" in settings.SOLR_CONNECTIONS["default"]:
            test_config.update(settings.SOLR_CONNECTIONS["default"]["TEST"])

        # if test collection is not explicitly configured,
        # set it based on default collection
        if (
            "TEST" not in test_config
            or "COLLECTION" not in settings.SOLR_CONNECTIONS["default"]["TEST"]
        ):
            test_config["COLLECTION"] = (
                "test_%s" % settings.SOLR_CONNECTIONS["default"]["COLLECTION"]
            )

        logger.info("Configuring Solr for tests %(URL)s%(COLLECTION)s", test_config)
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
        if not solr_config_opts:
            return

        logger.info(
            "Configuring Solr for tests %(URL)s%(COLLECTION)s", solr_config_opts
        )

        with override_settings(SOLR_CONNECTIONS={"default": solr_config_opts}):
            # reload core before and after to ensure field list is accurate
            solr = parasolr_django.SolrClient(commitWithin=10)
            response = solr.core_admin.status(core=solr_config_opts["COLLECTION"])
            if not response.status.get(solr_config_opts["COLLECTION"], None):
                solr.core_admin.create(
                    solr_config_opts["COLLECTION"],
                    configSet=solr_config_opts["CONFIGSET"],
                )

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
            solr.update.delete_by_query("*:*")
            # and unload
            solr.core_admin.unload(
                solr_config_opts["COLLECTION"],
                deleteInstanceDir=True,
                deleteIndex=True,
                deleteDataDir=True,
            )

    @pytest.fixture
    def empty_solr():
        """pytest fixture to clear out all content from configured Solr"""
        parasolr_django.SolrClient().update.delete_by_query("*:*")
        while parasolr_django.SolrQuerySet().count() != 0:
            # sleep until we get records back; 0.1 seems to be enough
            # for local dev with local Solr
            sleep(0.1)


def get_mock_solr_queryset(spec=SolrQuerySet, extra_methods=[]):
    mock_qs = MagicMock(spec=spec)

    # simulate fluent interface
    for meth in [
        "filter",
        "facet",
        "stats",
        "facet_field",
        "facet_range",
        "search",
        "order_by",
        "query",
        "only",
        "also",
        "highlight",
        "raw_query_parameters",
        "all",
        "none",
    ] + extra_methods:
        getattr(mock_qs, meth).return_value = mock_qs

    return Mock(return_value=mock_qs)


@pytest.fixture
def mock_solr_queryset(request):
    """Fixture to provide a :class:`unitest.mock.Mock` for
    :class:`~parasolr.query.queryset.SolrQuerySet` that simplifies
    testing against a mocked version of the fluent interface. It returns
    a method to generate a Mock queryset class; the method has an
    optional parameter for a queryset subclass to use for the `spec`
    argument to Mock.

    If called from a class or function where the request provides access
    to a class, the mock generator method `mock_solr_queryset` will be
    added to the class as a static method.

    Example uses:

        @pytest.mark.usefixtures("mock_solr_queryset")
        class MyTestCase(TestCase):

            def test_my_solr_method(self):

                with patch('parasolr.queryset.SolrQuerySet',
                       new=self.mock_solr_queryset()) as mock_queryset_cls:

                    mock_qs = mock_queryset_cls.return_value
                    mock_qs.search.assert_any_call(text='my test search')

    To use with a custom queryset subclass::

        mock_qs = self.mock_solr_queryset(MySolrQuerySet)

    """

    # if scope is class or function and there is a class available,
    # convert the mock generator to a static method and set it on the class
    if request.scope in ["class", "function"] and getattr(request, "cls", None):
        request.cls.mock_solr_queryset = staticmethod(get_mock_solr_queryset)
    return get_mock_solr_queryset
