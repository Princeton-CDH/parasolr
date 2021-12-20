"""
Test pytest plugin fixture for django
"""
from unittest.mock import MagicMock, Mock, patch

import pytest

try:
    from django.conf import settings
    from django.test import override_settings

    from parasolr.pytest_plugin import get_test_solr_config

except ImportError:
    pass

from parasolr.pytest_plugin import get_mock_solr_queryset, mock_solr_queryset
from parasolr.query import SolrQuerySet
from parasolr.tests.utils import skipif_no_django

pytest_plugins = "pytester"


@skipif_no_django
class TestGetTestSolrConfig:
    def test_no_testconfig(self):
        no_test_cfg = {
            "default": {"URL": "http://example.com:8984/solr", "COLLECTION": "mycoll"}
        }
        with override_settings(SOLR_CONNECTIONS=no_test_cfg):
            test_cfg = get_test_solr_config()
            assert test_cfg["URL"] == no_test_cfg["default"]["URL"]
            assert (
                test_cfg["COLLECTION"]
                == "test_%s" % no_test_cfg["default"]["COLLECTION"]
            )

    def test_has_testconfig(self):
        cfg_with_test_cfg = {
            "default": {
                "URL": "http://example.com:8984/solr",
                "COLLECTION": "mycoll",
                "TEST": {
                    "URL": "http://testing.example.com:8985/solr",
                    "COLLECTION": "testing",
                    "COMMITWITHIN": 350,
                },
            }
        }
        with override_settings(SOLR_CONNECTIONS=cfg_with_test_cfg):
            test_cfg = get_test_solr_config()
            assert test_cfg["URL"] == cfg_with_test_cfg["default"]["TEST"]["URL"]
            assert (
                test_cfg["COLLECTION"]
                == cfg_with_test_cfg["default"]["TEST"]["COLLECTION"]
            )
            assert (
                test_cfg["COMMITWITHIN"]
                == cfg_with_test_cfg["default"]["TEST"]["COMMITWITHIN"]
            )


@skipif_no_django
def test_configure_django_test_solr(testdir):
    """Basic check of django solr pytest fixture."""

    solr_url = settings.SOLR_CONNECTIONS["default"]["URL"]
    solr_test_collection = settings.SOLR_CONNECTIONS["default"]["TEST"]["COLLECTION"]
    solr_commit_within = settings.SOLR_CONNECTIONS["default"]["TEST"]["COMMITWITHIN"]

    # NOTE: can't figure out how to get the plugin test to use
    # test-local test settings, so testing against project
    # testsettings for now

    # create a temporary pytest test file
    testdir.makepyfile(
        """
        from parasolr.django import SolrClient

        # causes "Plugin already registered" error on travis...
        # pytest_plugins = "parasolr.pytest_plugin"

        def test_solr_client():
            solr = SolrClient()
            # solr client should use test config
            assert solr.solr_url == '%s'
            test_collection = '%s'
            assert solr.collection == test_collection
            # should get test config for commit within
            assert solr.commitWithin == %d
            # core should exist
            assert solr.core_admin.status(core=test_collection)

    """
        % (solr_url, solr_test_collection, solr_commit_within)
    )

    # run all tests with pytest with all pytest-django plugins turned off
    # result = testdir.runpytest('-p', 'no:django')
    result = testdir.runpytest_subprocess("--capture", "no")
    # check that test case passed
    result.assert_outcomes(passed=1)


@skipif_no_django
def test_not_configured(testdir):
    """skip without error if not configured."""

    with override_settings(SOLR_CONNECTIONS=None):
        assert not get_test_solr_config()

        # create a temporary pytest test file with no solr use
        testdir.makepyfile(
            """
        def test_unrelated():
            assert 1 + 1 == 2
        """
        )
        # run all tests with pytest with all pytest-django plugins turned off
        result = testdir.runpytest_subprocess("--capture", "no")
        # check that test case passed
        result.assert_outcomes(passed=1)


@skipif_no_django
def test_app_not_installed(testdir):
    """skip without error if not configured."""

    with patch("parasolr.pytest_plugin.apps") as mockapps:
        mockapps.is_installed.return_value = False
        assert not get_test_solr_config()
        mockapps.is_installed.assert_called_with("parasolr")


@skipif_no_django
def test_empty_solr(testdir):
    """Check empty_solr pytest fixture."""

    # NOTE: can't figure out how to get the plugin test to use
    # test-local test settings, so testing against project
    # testsettings for now

    # create a temporary pytest test file
    testdir.makepyfile(
        """
        from parasolr.django import SolrClient

        # causes "Plugin already registered" error on travis...
        # pytest_plugins = "parasolr.pytest_plugin"

        def test_empty_solr(empty_solr):
            solr = SolrClient()
            assert solr.query(q='*:*').numFound == 0

    """
    )

    # run all tests with pytest with all pytest-django plugins turned off
    # result = testdir.runpytest('-p', 'no:django')
    result = testdir.runpytest_subprocess("--capture", "no")
    # check that test case passed
    result.assert_outcomes(passed=1)


def test_get_mock_solr_queryset():
    # mock queryset generator
    mock_qs_cls = get_mock_solr_queryset()
    assert isinstance(mock_qs_cls, Mock)

    mock_qs = mock_qs_cls()
    assert isinstance(mock_qs, MagicMock)
    assert isinstance(mock_qs, SolrQuerySet)

    # test a few of the methods that return the same mock
    assert mock_qs.filter() == mock_qs
    assert mock_qs.all() == mock_qs


def test_get_mock_solr_queryset_subclass():
    class MyCustomQuerySet(SolrQuerySet):
        def custom_method(self):
            """custom method queryset method to keep in mock"""

    # call the genreator with the subclass
    mock_qs_cls = get_mock_solr_queryset(MyCustomQuerySet)
    # generate a mock instance
    mock_qs = mock_qs_cls()
    # should be able to call the custom method (included in spec)
    mock_qs.custom_method()
    # should pass isinstance check
    assert isinstance(mock_qs, MyCustomQuerySet)

    # specify extra methods to include in fluent interface
    mock_qs_cls = get_mock_solr_queryset(
        MyCustomQuerySet, extra_methods=["custom_method"]
    )
    mock_qs = mock_qs_cls()
    assert mock_qs.custom_method.return_value == mock_qs


def test_get_mock_solr_queryset_class_scope(testdir):
    # test class scope logic when using mock solr queryset fixture

    # create a temporary pytest test file
    testdir.makepyfile(
        """
        import pytest
        # causes "Plugin already registered" error on travis...
        # pytest_plugins = "parasolr.pytest_plugin"

        class TestGetMockSolrQueryset:
            # test class scope logic when using mock solr queryset fixture

            @pytest.mark.usefixtures("mock_solr_queryset")
            def test_class_scope(self):
                # method should be set on the class
                assert self.mock_solr_queryset

    """
    )

    # run all tests with pytest with all pytest-django plugins turned off
    # result = testdir.runpytest('-p', 'no:django')
    result = testdir.runpytest_subprocess("--capture", "no")
    # check that test case passed
    result.assert_outcomes(passed=1)
