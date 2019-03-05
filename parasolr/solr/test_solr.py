from collections import OrderedDict
import pytest
import sys
import time
import uuid
from unittest.mock import patch, Mock

from attrdict import AttrDict
import requests

from parasolr.solr.base import CoreExists, ClientBase, ImproperConfiguration
from parasolr.solr.client import SolrClient, QueryReponse
from parasolr.solr.schema import Schema
from parasolr.solr.update import Update
from parasolr.solr.admin import CoreAdmin
from parasolr import __version__ as parasolr_ver


# - Handling for test setttings intEgrated into CI flow.
try:
    from django import settings
except ImportError:
    # append top level working directory to path to add  testsettings
    sys.path.append('.')
    try:
        import testsettings as settings
    except ImportError:
        raise ImportError('No Django or parasolr test settings module found.')

try:
    TEST_SOLR_CONNECTION = settings.SOLR_CONNECTIONS['default']['TEST']
# reraise whether or not the key is missing for 'test' OR the entire setting
# is missing.
except (AttributeError, KeyError) as err:
   raise err.__class__(
        'Check that a SOLR_CONNECTIONS block with a "TEST" entry '
        'is defined.'
   )


# Any fields listed here will be cleaned up after every test,
# as they persist--even across a core being unloaded.
# If you add fields and don't update this list, unexpected behavior
# will almost certainly result.
TEST_FIELDS = ['A', 'B', 'C', 'D']

# Copy fields used in tests, with tuples of (source, dest)
TEST_COPY_FIELDS = [('A', 'B'), ('C', 'D')]

# Field types that need to be cleared after each run
TEST_FIELD_TYPES = ['test_A', 'test_B']

@pytest.fixture
def test_client(request):
    """Creates and returns a Solr core using TEST_SETTINGS, and then removes
    it on teardown, as well as all TEST_* fields.

    If a test field is listed here, it will NOT be automatically cleaned up.
    """

    solr_url = TEST_SOLR_CONNECTION.get('URL', None)
    collection = TEST_SOLR_CONNECTION.get('COLLECTION', None)
    commitWithin = TEST_SOLR_CONNECTION.get('COMMITWITHIN', None)

    if not solr_url or not collection:
        raise ImproperConfiguration(
            "Test client requires URL and COLLECTION in SOLR_CONNECTIONS."
        )


    client = SolrClient(solr_url, collection, commitWithin=commitWithin)

    response = client.core_admin.status(core=collection)
    if response.status.parasolr_test:
        raise CoreExists('Test core "parasolr_test" exists, aborting!')
    client.core_admin.create(collection, configSet='basic_configs')

    def clean_up():
        for field in TEST_FIELDS:
            client.schema.delete_field(field)
        for source, dest in TEST_COPY_FIELDS:
            client.schema.delete_copy_field(source=source, dest=dest)
        for ftype in TEST_FIELD_TYPES:
            client.schema.delete_field_type(name=ftype)
        client.core_admin.unload(
            collection,
            deleteInstanceDir=True,
            deleteIndex=True,
            deleteDataDir=True
        )

    request.addfinalizer(clean_up)
    return client

@pytest.fixture
def core_test_client(request):
    """Create a core name and pass an unconfigured client for it,
    along with name to fixture.

    Unconditionally deletes the core named, so that any CoreAdmin API tests
    are always cleaned up on teardown.
    """
    solr_url = TEST_SOLR_CONNECTION.get('URL', None)
    commitWithin  = TEST_SOLR_CONNECTION.get('COMMITWITHIN', None)

    if not solr_url:
        raise ImproperConfiguration(
            "Core admin test client requires URL setting in SOLR_CONNECTIONS."
        )


    core_name = str(uuid.uuid4())

    client = SolrClient(solr_url, core_name, commitWithin=commitWithin)

    def clean_up():

        client.core_admin.unload(
            core_name,
            deleteInstanceDir=True,
            deleteIndex=True,
            deleteDataDir=True
        )

    request.addfinalizer(clean_up)
    return (client, core_name)

class TestClientBase:

    def test_init(self):
        client_base = ClientBase()
        assert isinstance(client_base.session, requests.Session)

        # passing in a session causes that one to be set
        mocksession = Mock()
        client_base = ClientBase(session=mocksession)
        assert client_base.session == mocksession

    def test_build_url(self):
        client_base = ClientBase()
        url1 = client_base.build_url('http://foo/', 'bar', 'baz')
        assert url1 == 'http://foo/bar/baz'

    # patch so that we can intercept the request and get the
    # prepared request object
    @patch('parasolr.solr.base.requests.sessions.Session.send')
    def test_make_request(self, mocksend):
        client_base = ClientBase()
        client_base.session.headers = {
            'foo': 'bar'
        }
        client_base.make_request(
            'post',
            'http://localhost/',
            params={'a': 1, 'b': True},
            headers={'baz': 'bar'},
            data='foo'
        )
        # first arg of first call = PrepareRequest
        prep = mocksend.call_args[0][0]
        assert prep.method == 'POST'
        # params joined and json header added
        assert 'http://localhost/' in prep.url
        assert 'a=1' in prep.url
        assert 'b=true' in prep.url
        # headers concatenated from session
        assert prep.headers['foo'] == 'bar'
        assert prep.headers['baz'] == 'bar'
        assert prep.body == '"foo"'

        # test that error handling works for bad status_codes
        # and for solr sending an error
        # correct run returns an attrDict
        mockresp = Mock()
        mockresp.status_code = 200
        mockresp.json.return_value = {
            'responseHeader': {
                'status': 0,
                'QTime': 0
            }
        }
        mocksend.return_value = mockresp
        response = client_base.make_request(
            'post',
            'http://localhost/',
            params={'a': 1, 'b': True},
            headers={'baz': 'bar'},
            data='foo'
        )
        assert response.responseHeader.status == 0
        assert response.responseHeader.QTime == 0
        # an incorrect run by status code returns None
        mockresp.status_code = 400
        response = client_base.make_request(
            'post',
            'http://localhost/',
            params={'a': 1, 'b': True},
            headers={'baz': 'bar'},
            data='foo'
        )
        assert response is None
        # an incorrect run by Solr status code also returns None
        mockresp.status_code = 200
        mockresp.json.return_value['responseHeader']['status'] = 12
        mockresp.json.return_value['responseHeader']['errors'] = \
            {'something': 'went wrong'}
        response = client_base.make_request(
            'post',
            'http://localhost/',
            params={'a': 1, 'b': True},
            headers={'baz': 'bar'},
            data='foo'
        )
        assert response is None

        # test wrap = false
        mockresp = Mock()
        mockresp.status_code = 200
        mockresp.json.return_value = {
            'responseHeader': {
                'status': 0,
                'QTime': 0
            }
        }
        response = client_base.make_request('post', 'http://localhost/',
                                            wrap=False)
        assert not isinstance(response, AttrDict)


class TestQueryResponse:

    def test_init(self):

        response = AttrDict({
            'responseHeader': {
                'params': {'foo': 'bar'}
            },
            'response': {
                'numFound': 2,
                'start': 0,
                'docs': [
                    {'A': 5},
                    {'A': 2},
                    {'A': 3},
                ],
            },
            'facet_counts': {
                    'facet_fields': {
                        'A': ['5', 1, '2', 1, '3', 1]
                    },
                    'facet_ranges': {
                        'A': {
                            'counts': ['1', 1, '2', 2, '7', 1]
                        }
                    }
            },
        })
        qr = QueryReponse(response)
        assert qr.params == response.responseHeader.params
        assert qr.start == response.response.start
        assert qr.docs == response.response.docs
        assert qr.numFound == response.response.numFound
        assert isinstance(qr.facet_counts['facet_fields']['A'],
                          OrderedDict)
        assert isinstance(qr.facet_counts['facet_ranges']['A']['counts'],
                          OrderedDict)
        assert qr.facet_counts['facet_fields']['A']['5'] == 1
        assert qr.facet_counts['facet_ranges']['A']['counts']['2'] == 2


class TestSolrClient:

    def test_solr_client_init(self):
        solr_url = 'http://localhost:8983/solr'
        collection = 'testcoll'
        client = SolrClient(solr_url, collection)
        # check that args are respected
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
            'parasolr/%s (python-requests/%s)' % (parasolr_ver,
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
        test_client.schema.add_field(name='B', type='int')
        test_client.update.index([
            {'A': 'foo', 'B': 5, 'id': 1},
            {'A': 'bar', 'B': 20, 'id': 2},
            {'A': 'baz', 'B': 25, 'id': 3},
            {'A': 'baz', 'B': 30, 'id': 4},
        ])
        time.sleep(1)
        # get back two
        response = test_client.query(q='A:(bar OR baz)')
        assert response.numFound == 3
        # not paginated so should be starting at 0
        assert response.start == 0
        # should be the two expected documents
        # FIXME: these lines have no effect
        {'A': 'bar', 'B': 20, 'id': 2}
        {'A': 'baz', 'B': 25, 'id': 3} in response.docs
        {'A': 'baz', 'B': 30, 'id': 4} in response.docs

        # test faceting in response
        response = test_client.query(
            q='*:*',
            facet='on',
            **{
                'facet.field': 'A',
                'facet.range': 'B',
                'f.B.facet.range.start': 1,
                'f.B.facet.range.end': 25,
                'f.B.facet.range.gap': 10
            }
        )
        assert response.facet_counts
        assert response.facet_counts.facet_fields
        # must access using dict notation to get the OrderedDict as presented
        assert isinstance(response.facet_counts.facet_fields['A'], OrderedDict)
        assert response.facet_counts.facet_fields.A['bar'] == 1
        assert response.facet_counts.facet_fields.A['baz'] == 2
        assert isinstance(response.facet_counts.facet_ranges['B']['counts'],
                          OrderedDict)
        # check that the gaps are generated as expected
        assert response.facet_counts.facet_ranges['B']['counts']['1'] == 1
        assert response.facet_counts.facet_ranges['B']['counts']['11'] == 1

        # test wrap = False
        response = test_client.query(q='*:*', wrap=False)
        assert not isinstance(response, QueryReponse)


class TestUpdate:

    def test_init(self):

        up = Update('http://foo/', 'fake', 'update', commitWithin=1000)
        assert up.url == 'http://foo/fake/update'
        assert up.params['commitWithin'] == 1000

        mocksession = Mock()
        up = Update('http://foo/', 'fake', 'update', commitWithin=1000,
                      session=mocksession)
        assert up.session == mocksession

    def test_index(self, test_client):
        # add a field and index some documents
        test_client.schema.add_field(name='A', type='string')
        docs = [
            {'A': 'foo', 'id': 1},
            {'A': 'bar', 'id': 2},
            {'A': 'baz', 'id': 3}
        ]
        test_client.update.index(docs)
        time.sleep(1)
        resp = test_client.query(q='*:*')
        assert resp.numFound == 3
        a_list = list(map(lambda x: x.A, resp.docs))
        id_list = list(map(lambda x: int(x.id), resp.docs))
        for doc in docs:
            assert doc['A'] in a_list
            assert doc['id'] in id_list

        test_client.update.delete_by_query('*:*')
        time.sleep(1)
        test_client.update.index(docs, commit=True)
        time.sleep(1)
        resp = test_client.query(q='*:*')
        assert resp.numFound == 3
        # check that a quicker commit is passed along
        test_client.update.delete_by_query('*:*')
        time.sleep(1)
        test_client.update.index(docs, commitWithin=10)
        # this will fail with default commmit times
        time.sleep(0.8)
        resp = test_client.query(q='*:*')
        assert resp.numFound == 3

    def test_delete_by_id(self, test_client):
        # add a field and index some documents
        test_client.schema.add_field(name='A', type='string')
        docs = [
            {'A': 'foo', 'id': 1},
            {'A': 'bar', 'id': 2},
            {'A': 'baz', 'id': 3}
        ]
        test_client.update.index(docs)
        time.sleep(1)
        resp = test_client.query(q='*:*')
        assert resp.numFound == 3
        test_client.update.delete_by_id(1)
        time.sleep(1)
        resp = test_client.query(q='*:*')
        assert resp.numFound == 2
        a_list = list(map(lambda x: x.A, resp.docs))
        assert 'foo' not in a_list

    def test_delete_by_query(self, test_client):
        # add a field and index some documents
        test_client.schema.add_field(name='A', type='string')
        docs = [
            {'A': 'foo', 'id': 1},
            {'A': 'bar', 'id': 2},
            {'A': 'baz', 'id': 3}
        ]
        test_client.update.index(docs)
        time.sleep(1)
        resp = test_client.query(q='*:*')
        assert resp.numFound == 3
        test_client.update.delete_by_query('*:*')
        time.sleep(1)
        resp = test_client.query(q='*:*')
        assert resp.numFound == 0


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


    def test_list_fields(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        test_client.schema.add_field(name='B', type='int')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert fields[names.index('A')].type == 'string'
        assert fields[names.index('B')].type == 'int'
        # check that we can look for a subset of fields
        fields = test_client.schema.list_fields(fields=['A'])
        names = [f.name for f in fields]
        assert 'B' not in names
        fields = test_client.schema.list_fields(includeDynamic=True)
        names = [f.name for f in fields]
        # check that a stock dynamic field exists
        assert '*_txt_en' in names


    def test_add_copy_field(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        test_client.schema.add_field(name='B', type='string')

        test_client.schema.add_copy_field(source='A', dest='B', maxChars=80)

        cp_fields = test_client.schema.list_copy_fields()
        assert cp_fields[0].source == 'A'
        assert cp_fields[0].dest == 'B'
        assert cp_fields[0].maxChars == 80

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

    def test_list_copy_fields(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        test_client.schema.add_field(name='B', type='string')
        test_client.schema.add_field(name='C', type='int')
        test_client.schema.add_field(name='D', type='int')

        test_client.schema.add_copy_field(source='A', dest='B')
        test_client.schema.add_copy_field(source='C', dest='D')
        cp_fields = test_client.schema.list_copy_fields()
        assert cp_fields[0].source == 'A'
        assert cp_fields[0].dest == 'B'
        assert cp_fields[1].source == 'C'
        assert cp_fields[1].dest == 'D'
        # filter by source field
        ab = test_client.schema.list_copy_fields(source_fl=['A'])
        assert len(ab) == 1
        assert ab[0].source == 'A'
        assert ab[0].dest == 'B'
        # filter by dest field
        cd = test_client.schema.list_copy_fields(dest_fl=['D'])
        assert len(cd) == 1
        assert cd[0].source == 'C'
        assert cd[0].dest == 'D'

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

    def test_get_schema(self, test_client):
        schema = test_client.schema.get_schema()
        # check that we have the basic_configs schema
        assert schema.name == 'example-basic'

class TestCoreAdmin:

    def test_init(self):

        adm = CoreAdmin('http://foo/', 'admin')
        assert adm.url == 'http://foo/admin'

        mocksession = Mock()
        adm = CoreAdmin('http://foo/', 'admin', session=mocksession)
        assert adm.session == mocksession

    def test_create_unload(self, core_test_client):
        test_client, core = core_test_client
        test_client.core_admin.create(core, configSet='basic_configs')
        resp = test_client.core_admin.status(core=core)
        assert not resp.initFailures
        # core has a start time
        assert resp.status[core]['startTime']
        # clean up the core
        test_client.core_admin.unload(
            core,
            deleteInstanceDir=True,
            deleteIndex=True,
            deleteDataDir=True
        )
        # check that additional params (for the rest of the API)
        # can be used
        with patch('parasolr.solr.admin.ClientBase.make_request') as mockrequest:
            test_client.core_admin.create(core, configSet='basic_configs',
                                          dataDir='foo')
            assert mockrequest.called
            params = mockrequest.call_args[1]['params']
            assert params['name'] == core
            assert params['action'] == 'CREATE'
            assert params['dataDir'] == 'foo'
            assert params['configSet'] == 'basic_configs'

    def test_reload(self, test_client):
        assert test_client.core_admin.reload(test_client.collection)
        assert not test_client.core_admin.reload('foo')

    def test_ping(self, core_test_client):
        # ping should return false for non-existent core
        solrclient, core = core_test_client
        assert not solrclient.core_admin.ping(core)
        # create the core and then check it
        solrclient.core_admin.create(core, configSet='basic_configs',
                                      dataDir='foo')
        assert solrclient.core_admin.ping(core)

    def test_status(self, test_client):
        response = test_client.core_admin.\
                status(core=TEST_SOLR_CONNECTION['COLLECTION'])
        # no init failures happened
        assert not response.initFailures
        # status is not empty, and therefore has core info
        assert response.status.parasolr_test
        # check a few core traits to make sure a valid
        # response came back
        assert response.status.parasolr_test.name == 'parasolr_test'
        assert response.status.parasolr_test.startTime
