import pytest
import time


import requests


from parasol.solr.base import CoreExists
from parasol.solr.client import SolrClient
from parasol.solr.schema import Schema
from parasol.solr.update import Update
from parasol.solr.admin import CoreAdmin
from parasol import __version__ as parasol_ver



TEST_SETTINGS = {
    'solr_url': 'http://localhost:8983/solr/',
    'collection': 'parasol_test',
    # aggressive commitWithin for test only
    'commitWithin': 500
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
    client = SolrClient(**TEST_SETTINGS)

    response = client.core_admin.status(core=TEST_SETTINGS['collection'])
    if response.status.parasol_test:
        raise CoreExists('Test core "parasol_test" exists, aborting!')
    client.core_admin.create(TEST_SETTINGS['collection'],
                             configSet='basic_configs')

    def clean_up():
        for field in TEST_FIELDS:
            client.schema.delete_field(field)
        for source, dest in TEST_COPY_FIELDS:
            client.schema.delete_copy_field(source=source, dest=dest)
        for ftype in TEST_FIELD_TYPES:
            client.schema.delete_field_type(name=ftype)
        client.core_admin.unload(
            TEST_SETTINGS['collection'],
            deleteInstanceDir='true',
            deleteIndex='true',
            deleteDataDir='true'
        )

    request.addfinalizer(clean_up)
    return client


class TestSolrClient:

    def test_solr_client_init(self):
        solr_url = 'http://localhost:8983/solr'
        collection = 'testcoll'
        client = SolrClient(solr_url, collection)
        # check that development defaults and args are respected
        assert client.solr_url == 'http://localhost:8983/solr'
        assert client.collection == 'testcoll'
        assert client.schema_handler == 'schema'
        assert client.select_handler == 'select'
        assert client.update_handler == 'update'

        # check that api objects are set on the object as expected
        assert isinstance(client.schema, Schema)
        assert isinstance(client.update, Update)
        assert isinstance(client.core_admin, CoreAdmin)

        # test that sessions is a Session object
        assert isinstance(client.session, requests.Session)

        # test that session headers include the version name
        assert client.session.headers['User-Agent'] == \
            'parasol/%s (python-requests/%s)' % (parasol_ver,
                                                 requests.__version__)


    def test_query(self, test_client):
        # query of empty core produces the expected results
        # of no docs and no items
        response = test_client.query(q='*:*')
        assert response.numFound == 0
        assert response.start == 0
        assert not response.docs
        assert response.params['q'] == '*:*'
        assert response.params['wt'] == 'json'
        # add a field and index some documents
        test_client.schema.add_field(name='A', type='string')
        test_client.update.index([
            {'A': 'foo', 'id': 1},
            {'A': 'bar', 'id': 2},
            {'A': 'baz', 'id': 3}
        ])
        time.sleep(1)
        # get back two
        response = test_client.query(q='A:(bar OR baz)')
        assert response.numFound == 2
        # not paginated so should be starting at 0
        assert response.start == 0
        # should be the two expected documents
        {'A': 'bar', id: 2} in response.docs
        {'A': 'baz', id: 3} in response.docs


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