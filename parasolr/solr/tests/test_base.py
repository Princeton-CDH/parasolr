from unittest.mock import Mock, patch

from attrdict import AttrDict
import requests

from parasolr.solr.base import ClientBase


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
        assert isinstance(response, AttrDict)
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
