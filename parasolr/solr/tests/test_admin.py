from unittest.mock import Mock, patch

from parasolr.solr.admin import CoreAdmin
from parasolr.solr.tests.conftest import TEST_SOLR_CONNECTION

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

    def test_ping(self, core_test_client, caplog):
        # ping should return false for non-existent core
        solrclient, core = core_test_client
        assert not solrclient.core_admin.ping(core)
        # should not log the error since 404 is an allowed response for ping
        assert not caplog.records
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