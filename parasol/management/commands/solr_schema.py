'''
**solr_schema** is a custom manage command to update the configured
schema definition for the configured Solr instance.  Reports on the
number of fields that are added or updated, and any that are out of
date and were removed.

Example usage::

    python manage.py solr_schema

'''

from django.core.management.base import BaseCommand, CommandError

from parasol.solr import DjangoSolrClient
from parasol.schema import SolrSchema


class Command(BaseCommand):
    '''Configure Solr schema fields'''
    help = __doc__

    def handle(self, *args, **kwargs):
        '''Load Django solr client and project schema configuration
        and update schema field types and fields.'''

        solr = DjangoSolrClient()

        # find the schema configuration; error if not found or too many
        try:
            schema_config = SolrSchema.get_configuration()
        except Exception as err:
            raise CommandError(err)

        try:
            results = schema_config.configure_solr_fieldtypes(solr)
        except ConnectionError:
            raise CommandError('Error connecting to Solr. ' +
                               'Check your configuration and make sure Solr is running.')

        # report on what was done
        self.report_changes(results, 'field type')

        try:
            results = schema_config.configure_solr_fields(solr)
        except ConnectionError:
            raise CommandError('Error connecting to Solr. ' +
                               'Check your configuration and make sure Solr is running.')
        # report on what was done
        self.report_changes(results, 'field')

        # use solr core admin to trigger reload, so schema
        # changes take effect
        # still TODO
        # solr.core_admin.reload()

    def report_changes(self, results, label):
        '''Report counts for added, replaced, or deleted items.'''
        for action in ['added', 'replaced', 'deleted']:
            # if count is non-zero, report action + count + item label
            if results[action]:
                self.stdout.write(
                    '%s %d %s%s' %
                    (action.title(), results[action], label,
                     '' if results[action] == 1 else 's'))
