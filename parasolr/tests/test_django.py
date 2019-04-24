from unittest.mock import Mock, patch

import pytest

try:
    from django.core.exceptions import ImproperlyConfigured
    from django.test import override_settings

    from parasolr.django import SolrClient, SolrQuerySet, \
        AliasedSolrQuerySet

except ImportError:
    pass

from parasolr.tests.utils import skipif_no_django, skipif_django


@skipif_no_django
def test_django_solrclient():

    # check error handling

    # no config
    with override_settings(SOLR_CONNECTIONS=None):
        with pytest.raises(ImproperlyConfigured) as err:
            SolrClient()
        assert 'requires SOLR_CONNECTIONS in settings' in str(err)

    # config but no default
    with override_settings(SOLR_CONNECTIONS={'foo': 'bar'}):
        with pytest.raises(ImproperlyConfigured) as err:
            SolrClient()
        assert 'No "default" section in SOLR_CONNECTIONS configuration' in str(err)

    # default config but no URL
    with override_settings(SOLR_CONNECTIONS={'default': {'foo': 'bar'}}):
        with pytest.raises(ImproperlyConfigured) as err:
            SolrClient()
        assert 'No URL in default SOLR_CONNECTIONS configuration' in str(err)

    # url but no collection
    config = {'URL': 'http://my.solr.com:8943/solr'}
    with override_settings(SOLR_CONNECTIONS={'default': config}):
        solr = SolrClient()
        assert solr.solr_url == config['URL']
        assert solr.collection == ''

    # url and collection
    config['COLLECTION'] = 'mycore'
    with override_settings(SOLR_CONNECTIONS={'default': config}):
        solr = SolrClient()
        assert solr.solr_url == config['URL']
        assert solr.collection == config['COLLECTION']

    # commit within option
    config['COMMITWITHIN'] = 750
    with override_settings(SOLR_CONNECTIONS={'default': config}):
        solr = SolrClient()
        assert solr.commitWithin == 750

        # but passed in value takes precedence
        solr = SolrClient(commitWithin=7339)
        assert solr.commitWithin == 7339


@skipif_django
def test_no_django_solrclient():
    # should not be defined when django is not installed
    with pytest.raises(ImportError):
        from parasolr.solr.django import SolrClient


@skipif_no_django
@patch('parasolr.django.SolrClient')
def test_django_solrqueryset(mocksolrclient):
    # auto-initialize solr connection if not specified
    sqs = SolrQuerySet()
    mocksolrclient.assert_called_with()
    assert sqs.solr == mocksolrclient.return_value
    mocksolrclient.reset_mock()

    # use solr client if passed in
    mymocksolr = Mock(spec=SolrClient)
    sqs = SolrQuerySet(solr=mymocksolr)
    assert sqs.solr == mymocksolr
    mocksolrclient.assert_not_called()


@skipif_no_django
@patch('parasolr.django.SolrClient')
def test_django_aliasedsolrqueryset(mocksolrclient):

    class MyAliasedSolrQuerySet(AliasedSolrQuerySet):
        """extended version of AliasedSolrQuerySet for testing"""

        #: map app/readable field names to actual solr fields
        field_aliases = {
            'name': 'name_t',
            'year':'year_i',
            'has_info':'has_info_b',
        }

    # django queryset behavior: auto-initialize solr connection if not specified
    mysqs = MyAliasedSolrQuerySet()
    mocksolrclient.assert_called_with()
    assert mysqs.solr == mocksolrclient.return_value
    mocksolrclient.reset_mock()

    # alias queryset init: field list and reverse alias lookup populated
    assert mysqs.field_list
    assert mysqs.reverse_aliases
