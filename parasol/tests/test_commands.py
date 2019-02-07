from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
import pytest
import requests

from parasol import schema
from parasol.management.commands import solr_schema


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

    @patch('parasol.management.commands.solr_schema.SolrClient')
    def test_handle_connection_error(self, mocksolr):
        mocksolr.return_value.core_admin.ping.side_effect = \
            requests.exceptions.ConnectionError

        with pytest.raises(CommandError):
            solr_schema.Command().handle()

    @patch('parasol.management.commands.solr_schema.SolrClient')
    @patch('parasol.management.commands.solr_schema.SolrSchema')
    @patch('parasol.management.commands.solr_schema.input')
    def test_handle_no_core(self, mockinput, mocksolrschema, mocksolrclient):
        # using mock SolrSchema to avoid exception on get_configuration

        mocksolr = mocksolrclient.return_value
        mocksolr.collection = 'test-coll'
        mocksolr.core_admin.ping.return_value = False

        # simulate user says no when asked to create core
        mockinput.return_value = 'n'
        solr_schema.Command().handle()
        mockinput.assert_called_with(
            'Solr core %s does not exist. Create it? (y/n)' %
            mocksolr.collection)
        mocksolr.core_admin.create.assert_not_called()

        # simulate user says yes when asked to create core
        mockinput.reset_mock()
        mockinput.return_value = 'Y'
        solr_schema.Command().handle()
        # called once
        assert mockinput.call_count
        mocksolr.core_admin.create.assert_called_with(
            mocksolr.collection, configSet='basic_configs')

        # simulate no input requested
        mockinput.reset_mock()
        mocksolr.reset_mock()
        mocksolr.core_admin.ping.return_value = False
        solr_schema.Command().handle(noinput=True)
        # input not called, but create should be called
        mockinput.assert_not_called()
        assert mocksolr.core_admin.create.call_count

        # should work the same way from the command line
        mockinput.reset_mock()
        mocksolr.reset_mock()
        mocksolr.core_admin.ping.return_value = False
        call_command('solr_schema', noinput=True)
        # input not called, but create should be called
        mockinput.assert_not_called()
        assert mocksolr.core_admin.create.call_count

        # simulate collection does exist - no input or create
        mocksolr.reset_mock()
        mocksolr.core_admin.ping.return_value = True
        solr_schema.Command().handle()
        mockinput.assert_not_called()
        mocksolr.core_admin.create.assert_not_called()

    @patch('parasol.management.commands.solr_schema.SolrClient')
    @patch('parasol.management.commands.solr_schema.SolrSchema')
    def test_handle_no_schema(self, mocksolrschema, mocksolrclient):
        mocksolr = mocksolrclient.return_value
        mocksolr.collection = 'test-coll'
        mocksolr.core_admin.ping.return_value = True
        err_msg = 'No Solr schema configuration found'
        mocksolrschema.get_configuration.side_effect = Exception(err_msg)

        with pytest.raises(CommandError) as err:
            solr_schema.Command().handle()
        assert err_msg in str(err)

    @patch('parasol.management.commands.solr_schema.SolrClient')
    @patch('parasol.management.commands.solr_schema.SolrSchema')
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
