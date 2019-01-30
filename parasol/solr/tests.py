import pytest
import time

from parasol.solr.client import SolrClient, CoreForTestExists
from parasol.solr.schema import Schema
from parasol.solr.update import Update



TEST_SETTINGS = {
    'solr_url': 'http://localhost:8983/solr/',
    'collection': 'parasol_test'
}

@pytest.fixture
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
    response = client.core_admin.unload(
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

    def test_add_field(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert 'A' in names
        assert fields[names.index('A')].type == 'string'

    def test_delete_field(self, test_client):
        # add field and assert it exists
        test_client.schema.add_field(name='A', type='string')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert 'A' in names
        # delete it should not be there
        test_client.schema.delete_field(name='A')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert 'A' not in names

    def test_replace_fields(self, test_client):
        # add a field and assert that it exists
        # add field and assert it exists
        # NOTE: This is behaving strangely with the pytest core load/unload
        # So using 'B' so that it does not clash with the other tests.
        test_client.schema.add_field(name='B', type='string')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert 'B' in names
        test_client.schema.replace_field(name='B', type='int')
        fields = test_client.schema.list_fields()
        assert fields[names.index('B')].type == 'int'


