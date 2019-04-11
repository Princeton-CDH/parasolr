from io import StringIO
from unittest.mock import Mock, patch

import pytest
import requests

try:
    from django.core.management import call_command
    from django.core.management.base import CommandError
    from django.test import override_settings

    from parasolr.management.commands import solr_schema, index
except ImportError:
    pass

from parasolr.tests.utils import skipif_no_django


@skipif_no_django
class TestSolrSchemaCommand:

    def test_report_changes(self):
        counts = {'added': 3, 'replaced': 0, 'deleted': 1}
        cmd = solr_schema.Command()
        with patch.object(cmd, 'stdout') as mock_stdout:
            cmd.report_changes(counts, 'field')

            assert mock_stdout.write.call_count == 2
            mock_stdout.write.assert_any_call('Added 3 fields')
            mock_stdout.write.assert_any_call('Deleted 1 field')

            # nothing to report
            counts = {'added': 0, 'replaced': 0, 'deleted': 0}
            mock_stdout.reset_mock()
            cmd.report_changes(counts, 'field')
            assert mock_stdout.write.call_count == 0

    @patch('parasolr.management.commands.solr_schema.SolrClient')
    def test_handle_connection_error(self, mocksolr):
        mocksolr.return_value.core_admin.ping.side_effect = \
            requests.exceptions.ConnectionError

        with pytest.raises(CommandError):
            solr_schema.Command().handle()

    @patch('parasolr.management.commands.solr_schema.SolrClient')
    @patch('parasolr.management.commands.solr_schema.SolrSchema')
    @patch('parasolr.management.commands.solr_schema.input')
    def test_handle_core(self, mockinput, mocksolrschema, mocksolrclient):
        # using mock SolrSchema to avoid exception on get_configuration

        mocksolr = mocksolrclient.return_value
        mocksolr.collection = 'test-coll'
        mocksolr.core_admin.ping.return_value = False

        cmd = solr_schema.Command()
        cmd.stdout = StringIO()

        # simulate user says no when asked to create core

        mockinput.return_value = 'n'
        cmd.handle()
        mockinput.assert_called_with(
            'Solr core %s does not exist. Create it? (y/n) ' %
            mocksolr.collection)
        mocksolr.core_admin.create.assert_not_called()

        # simulate user says yes when asked to create core
        mockinput.reset_mock()
        mockinput.return_value = 'Y'
        with override_settings(SOLR_CONNECTIONS=\
            {'default': {'CONFIGSET': 'test_config'}}):

            cmd.handle()
            # called once
            assert mockinput.call_count
            mocksolr.core_admin.create.assert_called_with(
                mocksolr.collection, configSet='test_config')

            # simulate no input requested
            mockinput.reset_mock()
            mocksolr.reset_mock()
            mocksolr.core_admin.ping.return_value = False
            cmd.handle(noinput=True)
            # input not called, but create should be called
            mockinput.assert_not_called()
            assert mocksolr.core_admin.create.call_count

            # should work the same way from the command line
            mockinput.reset_mock()
            mocksolr.reset_mock()
            mocksolr.core_admin.ping.return_value = False
            call_command('solr_schema', noinput=True, verbosity=0)
            # input not called, but create should be called
            mockinput.assert_not_called()
            assert mocksolr.core_admin.create.call_count

            # simulate collection does exist - no input or create
            mocksolr.reset_mock()
            mocksolr.core_admin.ping.return_value = True
            cmd.handle()
            mockinput.assert_not_called()
            mocksolr.core_admin.create.assert_not_called()

    @patch('parasolr.management.commands.solr_schema.SolrClient')
    @patch('parasolr.management.commands.solr_schema.SolrSchema')
    def test_handle_no_schema(self, mocksolrschema, mocksolrclient):
        mocksolr = mocksolrclient.return_value
        mocksolr.collection = 'test-coll'
        mocksolr.core_admin.ping.return_value = True
        err_msg = 'No Solr schema configuration found'
        mocksolrschema.get_configuration.side_effect = Exception(err_msg)

        with pytest.raises(CommandError) as err:
            solr_schema.Command().handle()
        assert err_msg in str(err)

    @patch('parasolr.management.commands.solr_schema.SolrClient')
    @patch('parasolr.management.commands.solr_schema.SolrSchema')
    def test_handle(self, mocksolrschema, mocksolrclient):
        mocksolr = mocksolrclient.return_value
        mocksolr.collection = 'test-coll'
        mocksolr.core_admin.ping.return_value = True

        schema_config = mocksolrschema.get_configuration.return_value

        cmd = solr_schema.Command()
        with patch.object(cmd, 'report_changes') as mock_report:
            cmd.handle()
            # should get schema config
            mocksolrschema.get_configuration.assert_called_with()
            # should configure field types and report
            schema_config.configure_fieldtypes.assert_called_with(mocksolr)
            mock_report.assert_any_call(
                schema_config.configure_fieldtypes.return_value, 'field type')
            # should configure fields and report
            schema_config.configure_fields.assert_called_with(mocksolr)
            mock_report.assert_any_call(
                schema_config.configure_fields.return_value, 'field')

            # should reload core
            mocksolr.core_admin.reload.assert_called_with(mocksolr.collection)


@skipif_no_django
class TestIndexCommand:

    @patch('parasolr.management.commands.index.Indexable')
    def test_index(self, mockindexable):
        # index data into solr and catch an error
        cmd = index.Command()
        cmd.solr = Mock()

        test_index_data = range(5)
        cmd.index(test_index_data)
        mockindexable.index_items.assert_called_with(test_index_data, progbar=None)

        # solr connection exception should raise a command error
        with pytest.raises(CommandError):
            mockindexable.index_items.side_effect = requests.exceptions.ConnectionError
            cmd.index(test_index_data)

    def test_clear(self):
        cmd = index.Command()
        cmd.solr = Mock()
        cmd.stdout = StringIO()

        cmd.clear('all')
        cmd.solr.update.delete_by_query.assert_called_with('*:*')

        cmd.solr.reset_mock()
        cmd.clear('work')
        cmd.solr.update.delete_by_query.assert_called_with('item_type:work')

        cmd.solr.reset_mock()
        cmd.clear('foo')
        cmd.solr.update.delete_doc_by_query.assert_not_called()

        cmd.stdout = StringIO()
        cmd.verbosity = 3
        cmd.clear('works')
        assert cmd.stdout.getvalue() == 'Clearing works from the index'

        cmd.stdout = StringIO()
        cmd.clear('all')
        assert cmd.stdout.getvalue() == 'Clearing everything from the index'

        # should also work from the command line
        with patch('parasolr.management.commands.index.SolrClient'):
            cmd.stdout.seek(0)
            call_command('index', index='none', clear='all', stdout=cmd.stdout)
            assert 'Clearing everything from the index' in cmd.stdout.getvalue()
            assert 'Indexed 0 items' in cmd.stdout.getvalue()

    @patch('parasolr.management.commands.index.Indexable')
    @patch('parasolr.management.commands.index.SolrClient')
    def test_handle_index_by_id(self, mocksolr, mockindexable):
        # create a mock indexable subclass to be returned by
        # mockindexable
        mock_indexable_model = Mock()
        mock_indexable_model.index_item_type.return_value = 'simple'
        mockindexable.all_indexables.return_value = [
            mock_indexable_model
        ]
        mockindexable.ID_SEPARATOR = '.'

        # patch the method that actually does the indexing (tested elsewhere)
        with patch.object(index.Command, 'index') as mock_index_meth:
            cmd = index.Command()
            cmd.stdout = StringIO()

            mock_index_meth.return_value = 1
            cmd.init_indexables()
            cmd.handle(index_ids=['simple.a', 'simple.b'], clear=None, no_progress=True)
            mock_indexable_model.objects.get.assert_any_call(pk='a')
            mock_indexable_model.objects.get.assert_any_call(pk='b')
            # items are indexed together in a single batch
            assert mock_index_meth.call_count == 1

            # handle id with unknown index label
            mock_index_meth.reset_mock()
            with pytest.raises(CommandError) as err:
                cmd.handle(index_ids=['foo.1'], clear=None, no_progress=True)
            assert not mock_index_meth.call_count
            assert "Unrecognized index id 'foo.1'" in str(err)

            # handle id without separator
            mock_index_meth.reset_mock()
            with pytest.raises(CommandError) as err:
                cmd.handle(index_ids=['foo:1'], clear=None, no_progress=True)
            assert not mock_index_meth.call_count
            assert "Unrecognized index id 'foo:1'" in str(err)

    @patch('parasolr.management.commands.index.progressbar')
    @patch('parasolr.management.commands.index.SolrClient')
    @patch('parasolr.indexing.SolrClient')
    def test_call_command(self, mocksolr, mocksolr2, mockprogbar):
        mocksolr = Mock()

        # patch the method that actually does the indexing (tested elsewhere)
        with patch.object(index.Command, 'index') as mock_index_meth:
            stdout = StringIO()
            # index method returns number of items indexed
            mock_index_meth.return_value = 6

            # index all indexable content
            call_command('index', index='all', stdout=stdout)
            # should be called once for each indexable subclass
            assert mock_index_meth.call_count == 2
            # call order is not guaranteed, not inspecting here
            # commit called after works are indexed
            mocksolr2.return_value.update.index.assert_called_with([], commit=True)
        # self.solr.update.index([], commit=True)
            # mocksolr.commit.assert_called_with(test_coll, openSearcher=True)

            # progressbar should be initialized and finished
            mockprogbar.ProgressBar.assert_called_with(
                redirect_stdout=True, max_value=6)
            mockprogbar.ProgressBar.return_value.finish.assert_called_with()

            # request no progress bar
            mockprogbar.reset_mock()
            call_command('index', index='all', no_progress=True, stdout=stdout)
            mockprogbar.ProgressBar.assert_not_called()

            # request single type; not enough data to run progress bar
            mockprogbar.reset_mock()
            mock_index_meth.reset_mock()
            call_command('index', index='simple', no_progress=True, stdout=stdout)
            mockprogbar.ProgressBar.assert_not_called()
            # should only be called once
            assert mock_index_meth.call_count == 1

            # index nothing
            mock_index_meth.reset_mock()
            call_command('index', index='none', stdout=stdout)
            assert not mock_index_meth.call_count
