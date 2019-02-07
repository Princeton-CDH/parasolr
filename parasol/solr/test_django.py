import pytest

try:
    import django
    from django.core.exceptions import ImproperlyConfigured
    from django.test import override_settings

    from parasol.solr.django import SolrClient

except ImportError:
    django = None


requires_django = pytest.mark.skipif(django is None,
                                     reason="requires Django")

@requires_django
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
