"""
Test pytest plugin fixture for django
"""
import uuid

import pytest
try:
    from django.conf import settings
    from django.test import override_settings
except ImportError:
    pass

from parasol.tests.utils import skipif_no_django


pytest_plugins = "pytester"


@skipif_no_django
def test_configure_django_test_solr(testdir):
    """Sanity check pytest solr fixture."""

    solr_url = settings.SOLR_CONNECTIONS['default']['URL']
    solr_collection = settings.SOLR_CONNECTIONS['default']['COLLECTION']

    # create a temporary pytest test file
    testdir.makepyfile(
        """
        from parasol.django import SolrClient

        # pytest_plugins = "parasol.pytest_plugin"

        def test_solr_client():
            solr = SolrClient()
            # solr client should use test config
            assert solr.solr_url == '%s'
            test_collection = 'test_%s'
            assert solr.collection == test_collection
            # core should exist
            assert solr.core_admin.status(core=test_collection)

    """ % (solr_url, solr_collection)
    )

    # run all tests with pytest with all pytest-django plugins turned off
    # result = testdir.runpytest('-p', 'no:django')
    result = testdir.runpytest_subprocess('--capture', 'no') #, '-p', 'no:django')
    # check that test case passed
    result.assert_outcomes(passed=1)
