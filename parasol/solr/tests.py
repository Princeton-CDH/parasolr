import pytest

from parasol.solr.client import SolrClient, CoreForTestExists
from parasol.solr.schema import Schema
from parasol.solr.update import Update



TEST_SETTINGS = {
    'solr_url': 'http://localhost:8983/solr/',
    'collection': 'parasol_test'
}

@pytest.fixture(scope='function')
def test_client():
    client = SolrClient(**TEST_SETTINGS)
    response  = client.core_admin.status(core=TEST_SETTINGS['collection'])
    # empty dict means the core does not exist
    if response.status.parasol_test != {}:
        raise CoreForTestExists('The test core, parasol_test, already exists, '
                                'not clearing! Please delete or rename it to '
                                'continue.')
    client.core_admin.create(
        TEST_SETTINGS['collection'],
        configSet='basic_configs')
    yield client
    client.core_admin.unload(
        TEST_SETTINGS['collection'],
        deleteInstanceDir='true'
    )


class TestSolrClient:

    def test_solr_client_init(self):
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
        client = SolrClient(
            collection='foobar',
            select_handler='bazbar',
            other='other')
        assert client.collection == 'foobar'
        assert client.select_handler == 'bazbar'
        assert client.other == 'other'

@pytest.mark.usefixtures("test_client")
class TestSchema:

    def test_add_field(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert 'A' in names
        assert fields[names.index('A')].type == 'string'




