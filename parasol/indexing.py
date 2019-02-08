import itertools
import logging

try:
    import django
    from django.db.models.query import QuerySet
except ImportError:
    django = None
    QuerySet = None

from parasol.solr.django import SolrClient


logger = logging.getLogger(__name__)


class Indexable:
    '''Mixin for objects that are indexed in Solr.  Subclasses must implement
    `index_id` and `index` methods.
    '''

    #: number of items to index at once when indexing a large number of items
    index_chunk_size = 150

    #: solr connection
    solr = None

    def __init__(self):
        # initialize connection to solr on first instance initialization
        Indexable._init_solr()

    @classmethod
    def _init_solr(cls):
        # store on the class to take advantage of sessions
        if cls.solr is None:
            cls.solr = SolrClient()

    @classmethod
    def all_indexables(cls):
        '''Find all :class:`Indexable` subclasses for indexing.'''
        return cls.__subclasses__()

    def index_item_type(self):
        '''Label for this kind of indexable item. Must be unique
        across all Indexable items in an application. By default, uses
        Django model verbose name. Used in default index id and
        in index manage command. '''
        return self._meta.verbose_name

    def index_id(self):
        '''Solr identifier. By default, combines :meth:`index item_type`
        and :attr:`id`.'''
        return '{}.{}'.format(self.index_item_type(), self.id)

    def index_data(self):
        '''Dictionary of data to index in Solr for this item.
        Default implementation  adds  :meth:`index_id` and
        :meth:`index_item_type'''
        return {
            'id': self.index_id(),
            'item_type': self.index_item_type()
        }

    def index(self):
        '''Index the current object in Solr.  Allows passing in
        parameter, e.g. to set a `commitWithin` value.
        '''
        self.solr.update.index([self.index_data()])

    @classmethod
    def index_items(cls, items, progbar=None):
        '''Indexable class method to index multiple items at once.  Takes a
        list, queryset, or generator of Indexable items or dictionaries.
        Items are indexed in chunks, based on :attr:`Indexable.index_chunk_size`.
        Takes an optional progressbar object to update when indexing items
        in chunks. Returns a count of the number of items indexed.'''

        # make sure solr client is initialized
        Indexable._init_solr()

        # if this is a queryset, use iterator to get it in chunks
        if QuerySet and isinstance(items, QuerySet):
            items = items.iterator()

        # if this is a normal list, convert it to an iterator
        # so we don't iterate the same slice over and over
        elif isinstance(items, list):
            items = iter(items)

        # index in chunks to support efficiently indexing large numbers
        # of items (adapted from index script)
        chunk = list(itertools.islice(items, cls.index_chunk_size))
        count = 0
        while chunk:
            # call index data method if present; otherwise assume item is dict
            cls.solr.update.index(
                [i.index_data() if hasattr(i, 'index_data') else i
                 for i in chunk])
            count += len(chunk)
            # update progress bar if one was passed in
            if progbar:
                progbar.update(count)

            # get the next chunk
            chunk = list(itertools.islice(items, cls.index_chunk_size))

        return count

    def remove_from_index(self):
        '''Remove the current object from Solr by identifier using
        :meth:`index_id`'''
        # NOTE: using quotes on id to handle ids that include colons or other
        # characters that have meaning in Solr/lucene queries
        logger.debug('Deleting document from index with id %s', self.index_id())
        self.solr.update.delete_by_id([self.index_id()])
