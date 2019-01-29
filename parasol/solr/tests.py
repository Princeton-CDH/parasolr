from parasol.solr.client import SolrClient
from parasol.solr.schema import Schema
from parasol.solr.update import Update


def test_solr_client_init():
    client = SolrClient()
    # check that development defaults are respected
    assert client.solr_url == 'http://localhost:8983/solr'
    assert client.collection == ''
    assert client.schema_handler == 'schema'
    assert client.select_handler == 'select'
    assert client.update_handler == 'update'
    # check that api objects are set on the object as expected
    assert isinstance(client.schema, Schema)
    assert isinstance(client.update, Update)
    # check that kwargs are added as properties and overwritten
    client = SolrClient(collection='foobar', select_handler='bazbar', other='other')
    assert client.collection == 'foobar'
    assert client.select_handler == 'bazbar'
    assert client.other == 'other'


