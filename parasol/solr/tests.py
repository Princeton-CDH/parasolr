import pytest
import time
import uuid

from parasol.solr.client import SolrClient, CoreForTestExists
from parasol.solr.schema import Schema
from parasol.solr.update import Update



TEST_SETTINGS = {
    'solr_url': 'http://localhost:8983/solr/',
}

# Any fields listed here will be cleaned up after every test,
# as they persist--even across a core being unloaded.
TEST_FIELDS = ['A']

# Copy fields used in tests, with tuples of (source, dest)
TEST_COPY_FIELDS = [('A', 'B')]


@pytest.fixture
def test_client(request):
    # create using uuid4, so almost certainly non-clashing
    core = uuid.uuid4()
    client = SolrClient(TEST_SETTINGS['solr_url'], collection=core)
    client.core_admin.create(core, configSet='basic_configs')

    def clean_up():
        for field in TEST_FIELDS:
            client.schema.delete_field(field)
        for source, dest in TEST_COPY_FIELDS:
            client.schema.delete_copy_field(source=source, dest=dest)
        client.core_admin.unload(
            core,
            deleteInstanceDir='true',
            deleteIndex='true',
            deleteDataDir='true'
        )

    request.addfinalizer(clean_up)
    return client


class TestSolrSchema:

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

class TestSchema:

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

        test_client.schema.add_field(name='A', type='string')
        test_client.schema.replace_field(name='A', type='int')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert fields[names.index('A')].type == 'int'

    def test_add_copy_field(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        test_client.schema.add_copy_field(source='A', dest='B')
        cp_fields = test_client.schema.list_copy_fields()
        assert cp_fields[0].source == 'A'
        assert cp_fields[0].dest == 'B'

    def test_delete_copy_field(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        test_client.schema.add_copy_field(source='A', dest='B')
        cp_fields = test_client.schema.list_copy_fields()
        assert cp_fields[0].source == 'A'
        assert cp_fields[0].dest == 'B'
        test_client.schema.delete_copy_field(source='A', dest='B')
        cp_fields = test_client.schema.list_copy_fields()
        # only copy field should be deleted
        assert len(cp_fields) == 0
