import time
from unittest.mock import Mock, patch

from parasolr.solr.update import Update

# NOTE: Field and field-type names must be registered and cleaned
# up in conftest.py
# Otherwise, they will be retained between test iterations and break results.


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

    def test_index_override(self, test_client):
        with patch.object(test_client.update, 'make_request') as mock_make_request:
            # ensure default is properly configured
            test_client.update.index([])
            args, kwargs = mock_make_request.call_args
            assert kwargs['params']['commitWithin'] == test_client.commitWithin

            # ensure commitWithin updates with index
            test_client.update.index([], commitWithin=1234)
            args, kwargs = mock_make_request.call_args
            assert kwargs['params']['commitWithin'] == 1234

            # ensure a hard commit removes the commitWithin default param and
            #  configures the new commit param
            test_client.update.index([], commit=True)
            args, kwargs = mock_make_request.call_args
            assert 'commitWithin' not in kwargs['params']
            assert kwargs['params']['commit']


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