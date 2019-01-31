'''
**solr_schema** is a custom manage command to update the configured
schema definition for the configured Solr instance.  Reports on the
number of fields that are added or updated, and any that are out of
date and were removed.

Example usage::

    python manage.py solr_schema

'''

from django.core.management.base import BaseCommand, CommandError

from parasol.solr import SolrClient
from parasol.schema import SolrSchema


class Command(BaseCommand):
    '''Configure Solr schema fields'''
    help = __doc__

    def handle(self, *args, **kwargs):
        print("***parasol solr_schema")

        # django solrclient still todo
        solr = SolrClient(url='http://localhost:8983/solr/',
            collection='parasol-ppa')

        # find the appropriate subclass
        # TODO: command error if exception
        schema_config = SolrSchema.get_configuration()

        try:
            created, updated, removed = schema_config.update_solr_fields(solr)
        except ConnectionError:
            raise CommandError('Error connecting to Solr. ' +
                               'Check your configuration and make sure Solr is running.')
        # summarize what was done
        if created:
            self.stdout.write('Added %d field%s' %
                              (created, '' if created == 1 else 's'))
        if updated:
            self.stdout.write('Updated %d field%s' %
                              (updated, '' if updated == 1 else 's'))
        if removed:
            self.stdout.write('Removed %d field%s' %
                              (removed, '' if removed == 1 else 's'))

        # use solr core admin to trigger reload, so schema
        # changes take effect
        # still TODO
        # solr.core_admin.reload()
