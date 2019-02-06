'''
**solr_schema** is a custom manage command to update the configured
schema definition for the configured Solr instance.  Reports on the
number of fields that are added or updated, and any that are out of
date and were removed.

Example usage::

    python manage.py solr_schema

'''

from django.core.management.base import BaseCommand, CommandError
from requests.exceptions import ConnectionError

from parasol.solr import DjangoSolrClient
from parasol.schema import SolrSchema


class Command(BaseCommand):
    '''Configure Solr schema fields and field types.'''
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Do NOT prompt for user input'
        )

    def handle(self, *args, **kwargs):
        '''Load Django solr client and project schema configuration
        and update schema field types and fields.'''

        solr = DjangoSolrClient()
        noinput = kwargs.get('noinput', False)

        # check Solr connection and core exists
        try:
            core_exists = solr.core_admin.ping(solr.collection)
        except ConnectionError:
            raise CommandError("Error connecting to Solr. Check your " +
                               "configuration and make sure Solr is running")

        # if core does not exist, create it
        if not core_exists:
            # in no input mode, automatically create the core
            if noinput:
                create = True
            # otherwise, prompt the user to confirm
            else:
                create = input('Solr core %s does not exist. Create it? (y/n)' %
                               solr.collection).lower() == 'y'
            if create:
                solr.core_admin.create(solr.collection,
                                       configSet='basic_configs')
            else:
                # if core was not created, bail out
                return

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
