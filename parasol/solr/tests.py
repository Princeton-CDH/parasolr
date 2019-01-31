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
TEST_FIELDS = ['A', 'B']

# Copy fields used in tests, with tuples of (source, dest)
TEST_COPY_FIELDS = [('A', 'B')]

# Field types that need to be cleared after each run
TEST_FIELD_TYPES = ['test_A', 'test_B']

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
        for ftype in TEST_FIELD_TYPES:
            client.schema.delete_field_type(name=ftype)
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
        test_client.schema.add_field(name='B', type='string')

        test_client.schema.add_copy_field(source='A', dest='B')

        cp_fields = test_client.schema.list_copy_fields()
        assert cp_fields[0].source == 'A'
        assert cp_fields[0].dest == 'B'

    def test_delete_copy_field(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        test_client.schema.add_field(name='B', type='string')

        test_client.schema.add_copy_field(source='A', dest='B')

        cp_fields = test_client.schema.list_copy_fields()
        assert cp_fields[0].source == 'A'
        assert cp_fields[0].dest == 'B'
        test_client.schema.delete_copy_field(source='A', dest='B')
        cp_fields = test_client.schema.list_copy_fields()
        # only copy field should be deleted
        assert len(cp_fields) == 0

    def test_add_field_type(self, test_client):
        test_client.schema.add_field_type(
            name='test_A',
            # handle situations where we need class as kwarg
            klass='solr.TextField'
        )
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        assert 'test_A' in names
        assert field_types[names.index('test_A')]['class'] == 'solr.TextField'

    def test_delete_field_type(self, test_client):
        # create the field type
        test_client.schema.add_field_type(
            name='test_A',
            # handle situations where we need class as kwarg
            klass='solr.TextField'
        )
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        assert 'test_A' in names
        assert field_types[names.index('test_A')]['class'] == 'solr.TextField'
        # delete the field type
        test_client.schema.delete_field_type(name='test_A')
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        assert 'test_A' not in names

    def test_replace_field_type(self, test_client):
        # create the field type
        test_client.schema.add_field_type(
            name='test_A',
            # handle situations where we need class as kwarg
            klass='solr.TextField'
        )
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        assert 'test_A' in names
        assert field_types[names.index('test_A')]['class'] == 'solr.TextField'
        # replace it and check that the change was made
        test_client.schema.replace_field_type(
            name='test_A',
            klass='solr.StrField'
        )
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        assert 'test_A' in names
        assert field_types[names.index('test_A')]['class'] == 'solr.StrField'

    def test_list_field_types(self, test_client):
        # create two field types
        test_client.schema.add_field_type(
            name='test_A',
            klass='solr.StrField'
        )
        test_client.schema.add_field_type(
            name='test_B',
            # handle situations where we need class as kwarg
            klass='solr.TextField'
        )
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        # check that both are in field types, as defined
        assert 'test_A' in names
        assert field_types[names.index('test_A')]['class'] == 'solr.StrField'
        assert 'test_B' in names
        assert field_types[names.index('test_B')]['class'] == 'solr.TextField'
