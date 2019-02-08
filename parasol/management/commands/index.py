'''
**index** is a custom manage command to index content into Solr.  It
should only be run *after* your schema has been configured via
**solr_schema**.

By default, indexes _all_ indexable content.
TODO
You can optionally specify ***, or index specific items
by index id.

A progress bar will be displayed by default if there are more than 5
items to process.  This can be suppressed via script options.

You may optionally request the index or part of the index to be cleared
before indexing, for use when index data has changed sufficiently that
previous versions need to be removed.

Example usage::

    # index everything
    python manage.py index
    # index specific items
    python manage.py index htid1 htid2 htid3
    # index works only (skip pages)
    python manage.py index -i works
    python manage.py index --works
    # index pages only (skip works)
    python manage.py index -i pages
    python manage.py index ---pages
    # suppress progressbar
    python manage.py index --no-progress
    # clear everything, then index everything
    python manage.py index --clear all
    # clear works only, then index works
    python manage.py index --clear works --index works
    # clear everything, index nothing
    python manage.py index --clear all --index none

'''

from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import pluralize
import progressbar

from parasol.solr.django import SolrClient
from parasol.indexing import Indexable


class Command(BaseCommand):
    '''Index content in Solr'''
    help = __doc__

    solr = None

    options = {}
    #: normal verbosity level
    v_normal = 1
    verbosity = v_normal

    indexables = {}

    def init_indexables(self):
        # find all indexable models and create a dictionary
        # keyed on index item type
        self.indexables = {model.index_item_type(): model
                           for model in Indexable.all_indexables()}

    def add_arguments(self, parser):
        self.init_indexables()
        # indexing choices: all, none, and all indexable model names
        choices = ['all'] + list(self.indexables.keys())
        # allow indexing none so you can clear without indexing
        index_choices = choices + ['none']

        parser.add_argument(
            'index_ids', nargs='*',
            help='List of specific items to index (optional)')
        parser.add_argument(
            '-i', '--index', choices=index_choices, default='all',
            help='Index all items or one content type (by default indexes all)')
        parser.add_argument(
            '--no-progress', action='store_true',
            help='Do not display progress bar to track the status of the reindex.')
        parser.add_argument(
            '-c', '--clear', choices=choices, required=False,
            help='Clear some or all indexed data before reindexing')

    def handle(self, *args, **kwargs):
        self.solr = SolrClient()
        self.verbosity = kwargs.get('verbosity', self.v_normal)
        self.options = kwargs

        # clear index if requested
        if self.options['clear']:
            self.clear(self.options['clear'])

        total_to_index = 0
        to_index = []

        # index specific items by id
        if self.options['index_ids']:
            # NOTE: could probably query more efficiently, but this is
            # for manual id entry so should never be very many at once
            for index_id in self.options['index_ids']:
                # relies on default format of index_id in indexable
                unrecognized_err = "Unrecognized index id '{}'".format(index_id)
                # error if id can not be split
                if '.' not in index_id:
                    raise CommandError(unrecognized_err)

                index_type, item_id = index_id.split('.')
                # error if split but index type is not found
                if index_type not in self.indexables:
                    raise CommandError(unrecognized_err)
                to_index.append(self.indexables[index_type].objects .get(pk=item_id))
            total_to_index = len(to_index)

        else:
            # calculate total to index across all indexables for current mode
            for name, model in self.indexables.items():
                if self.options['index'] in [name, 'all']:
                    total_to_index += model.objects.count()

        # initialize progressbar if requested and indexing more than 5 items
        progbar = None
        if not self.options['no_progress'] and total_to_index > 5:
            progbar = progressbar.ProgressBar(redirect_stdout=True,
                                              max_value=total_to_index)
        count = 0

        # index items requested
        if to_index:
            # list of objects already gathered
            count += self.index(to_index, progbar=progbar)

        else:
            # iterate over indexables by type and index if requested
            for name, model in self.indexables.items():
                if self.options['index'] in [name, 'all']:
                    # index in chunks and update progress bar
                    count += self.index(model.objects.all(), progbar=progbar)

        if progbar:
            progbar.finish()

        # commit all the indexed changes
        self.solr.update.index([], commit=True)

        # report total items indexed
        if self.verbosity >= self.v_normal:
            self.stdout.write('Indexed {:,} item{}'.format(
                count, pluralize(count)))

    def index(self, index_data, progbar=None):
        '''index an iterable into the configured solr instance
        and solr collection'''

        # NOTE: currently no good way to catch a connection
        # error when Solr is not running because we get multiple
        # connections during handling of exceptions.
        try:
            # index in chunks and update progress bar if there is one
            return Indexable.index_items(index_data, progbar=progbar)
        except Exception as err:
            # TODO: test with new SolrClient code
        # except (ConnectionError, RequestException) as err:
            # NOTE: this is fairly ugly, and catching the more specific errors
            # doesn't work because there are multiple exceptions
            # thrown when a connection error occurs; however, this will
            # at least stop the script instead of repeatedly throwing
            # connection errors
            raise CommandError(err)

    def clear(self, mode):
        '''Remove items from the Solr index.  Mode should be 'all" or
        or an item type for a configured indexable.'''
        if mode == 'all':
            del_query = '*:*'
        else:
            # construct query based on item type
            del_query = 'item_type:{}'.format(mode)

        if self.verbosity >= self.v_normal:
            # pluralize indexable names but not all
            label = 'everything' if mode == 'all' else '%s' % mode
            self.stdout.write('Clearing %s from the index' % label)

        # return value doesn't tell us anything useful, so nothing
        # to return here
        self.solr.update.delete_by_query(del_query)
