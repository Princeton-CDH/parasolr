"""
Model-based indexing with Solr.

Items to be indexed in Solr should extend :class:`Indexable`. The
default implementation should work for most Django models; at a minimum
you should extend :meth:`Indexable.index_data` to include the information
to be indexed in Solr. You may also customize :meth:`Indexable.index_item_type`
and :meth:`Indexable.index_item_id`.

To manually index content in Solr, see
:mod:`~parasolr.management.commands.index` manage command documentation.

-------------------------

"""

import itertools
import logging

try:
    from django.db.models.query import QuerySet

    from parasolr.django import SolrClient
except ImportError:
    QuerySet = SolrClient = None


logger = logging.getLogger(__name__)


# recursive subclasses
# via https://stackoverflow.com/questions/3862310/how-to-find-all-the-subclasses-of-a-class-given-its-name
def all_subclasses(cls):
    """recursive method to find all subclasses"""
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]
    )


class Indexable:
    """Mixin for objects that are indexed in Solr.  Subclasses must implement
    `index_id` and `index` methods.

    When implementing an Indexable subclass where items_to_index
    returns something like a generator, which does not expose either a
    `count` method or can be counted with `len`, for use with
    the Django index manage command you should
    implement `total_to_index` and return the number of items
    to be indexed.
    """

    # NOTE: current implementation is Django-specific, intended for
    # use with django models. Should be possible to generalize once
    # we have other use cases.

    #: number of items to index at once when indexing a large number of items
    index_chunk_size = 150

    #: solr connection
    solr = None

    #: id separator for auto-generated index ids
    ID_SEPARATOR = "."

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
        """Find all :class:`Indexable` subclasses for indexing. Ignore abstract
        :class:`Indexable` subclasses such as
        :class:`~parasolr.django.indexing.ModelIndexable`."""
        return [
            subclass
            for subclass in all_subclasses(cls)
            if not hasattr(subclass, "_meta")
            or not getattr(subclass._meta, "abstract", False)
        ]

    @classmethod
    def index_item_type(cls):
        """Label for this kind of indexable item. Must be unique
        across all Indexable items in an application. By default, uses
        Django model verbose name. Used in default index id and
        in index manage command."""
        # TODO: move this implementation into django subclass?
        # default could just return an attribute on the class
        return cls._meta.verbose_name

    @classmethod
    def items_to_index(cls):
        """Get all items to be indexed for a single class of Indexable
        content. Subclasses can override this method to return a custom
        iterable, e.g. a Django `QuerySet` that takes advantage of
        prefetching. By default, returns all Django objects for a model.
        Raises NotImplementedError if that fails."""
        try:
            return cls.objects.all()
        except AttributeError:
            raise NotImplementedError

    @classmethod
    def total_to_index(cls):
        """Get the total number of items to be indexed for a single class of
        Indexable content. Subclasses should override this method
        if necessary. By default, returns a Django queryset count for a model.
        Raises NotImplementedError if that fails."""
        try:
            return cls.objects.count()
        except AttributeError:
            raise NotImplementedError

    def index_id(self):
        """Solr identifier. By default, combines :meth:`index item_type`
        and :attr:`id` with :attr:ID_SEPARATOR`."""
        return "%s%s%s" % (self.index_item_type(), self.ID_SEPARATOR, self.id)

    def index_data(self):
        """Dictionary of data to index in Solr for this item.
        Default implementation adds  :meth:`index_id` and
        :meth:`index_item_type`"""
        return {"id": self.index_id(), "item_type_s": self.index_item_type()}

    def index(self):
        """Index the current object in Solr."""
        self.solr.update.index([self.index_data()])

    @classmethod
    def index_items(cls, items, progbar=None):
        """Indexable class method to index multiple items at once.  Takes a
        list, queryset, or generator of Indexable items or dictionaries.
        Items are indexed in chunks, based on :attr:`Indexable.index_chunk_size`.

        Args:
            items: list, queryset, or generator of indexable objects or dictionaries
            progbar: optional :class:`progressbar.Progressbar` object to
            update when indexing items in chunks.

        Returns:
            Total number of items indexed
        """

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
                [i.index_data() if hasattr(i, "index_data") else i for i in chunk]
            )
            count += len(chunk)
            # update progress bar if one was passed in
            if progbar:
                progbar.update(count)

            # get the next chunk
            chunk = list(itertools.islice(items, cls.index_chunk_size))

        return count

    def remove_from_index(self):
        """Remove the current object from Solr by identifier using
        :meth:`index_id`"""
        # NOTE: using quotes on id to handle ids that include colons or other
        # characters that have meaning in Solr/lucene queries
        logger.debug("Deleting document from index with id %s", self.index_id())
        self.solr.update.delete_by_id([self.index_id()])
