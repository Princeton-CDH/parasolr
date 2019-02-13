"""
Object-oriented approach to Solr searching and filtering modeled
on :class:`django.models.queryset.QuerySet`.  Supports iteration,
slicing, counting, and boolean check to see if a search has results.

Filter, search and sort methods return a new queryset, and can be
chained. For example::

    SolrQuerySet().filter(item_type='person') \
                  .search(name='hem*') \
                  .order_by('sort_name') \


"""

from typing import Any, Optional, Dict, List

try:
    from parasol.solr.django import SolrClient
except ImportError:
    # FIXME: SolrQuerySet doesn't currently work with non-django
    # solr client because it would need a way to get connection settings
    from parasol.solr import SolrClient


class SolrQuerySet:
    """A Solr queryset object that allows for object oriented
    searching and filtering of Solr results. Allows search results
    to be paginated by django paginator."""

    _result_cache = None
    start = 0
    stop = None
    sort_options = []
    search_qs = []
    filter_qs = []
    #: by default, combine search queries with AND
    default_search_operator = 'AND'

    def __init__(self, solr: Optional[SolrClient] = None):
        self.solr = solr or SolrClient()
        # convert search operator into form needed for combining queries
        self._search_op = ' %s ' % self.default_search_operator

    def get_results(self, **kwargs) -> List[dict]:
        """
        Query Solr and get the results for the current query and filter
        options. Populates result cache and returns the documents portion
        of the reponse.

        Returns:
            Solr response documents as a list of dictionaries.
        """

        # TODO: can we store the result cache and only retrieve
        # if query options have changed?
        # For now, always query.

        query_opts = self.query_opts()
        query_opts.update(**kwargs)
        # TODO: what do we do about the fact that Solr defaults
        # to 10 rows?

        # NOTE: django templates choke on AttrDict because it is
        # callable; using dictionary response instead
        self._result_cache = self.solr.query(wrap=False, **query_opts)
        return self._result_cache['response']['docs']

    def query_opts(self) -> Dict[str, str]:
        """Construct query options based on current queryset configuration.
        Includes filter queries, start and rows, sort, and search query.
        """
        query_opts = {
            'start': self.start,
        }
        if self.filter_qs:
            query_opts['fq'] = self.filter_qs
        if self.stop:
            query_opts['rows'] = self.stop - self.start
        if self.sort_options:
            query_opts['sort'] = ','.join(self.sort_options)

        # main query; if no query is defined, find everything
        if self.search_qs:
            query_opts['q'] = self._search_op.join(self.search_qs)
        else:
            query_opts['q'] = '*:*'

        return query_opts

    def count(self) -> int:
        """Total number of results for the current query"""

        # if result cache is already populated, use it
        if self._result_cache is not None:
            return self._result_cache['response']['numFound']

        # otherwise, query with current options but request zero rows
        # and do not populate the result cache
        query_opts = self.query_opts()
        query_opts['rows'] = 0
        return self.solr.query(**query_opts, wrap=False)['response']['numFound']

    @staticmethod
    def _lookup_to_filter(key, value) -> str:
        """Convert keyword argument key=value pair into a Solr filter.
        Currently only supports simple case of field:value."""

        # NOTE: as needed, we can start implementing django-style filters
        # such as __in=[a, b, c] or __range=(start, end)
        return '%s:%s' % (key, value)

    def filter(self, *args, **kwargs):
        """
        Return a new SolrQuerySet with Solr filter queries added.
        """
        qs_copy = self._clone()

        # any args are treated as filter queries without modification
        qs_copy.filter_qs.extend(args)

        for key, value in kwargs.items():
            qs_copy.filter_qs.append(self._lookup_to_filter(key, value))

        return qs_copy

    def search(self, *args, **kwargs):
        """
        Return a new SolrQuerySet with search queries added. All
        queries will combined with the default search operator when
        constructing the `q` parameter sent to Solr..
        """
        qs_copy = self._clone()
        # any args are treated as search queries without modification
        qs_copy.search_qs.extend(args)

        for key, value in kwargs.items():
            qs_copy.search_qs.append(self._lookup_to_filter(key, value))

        return qs_copy

    def order_by(self, *args):
        """Apply sort options to the queryset by field name. If the field
        name starts with -, sort is descending; otherwise ascending."""
        qs_copy = self._clone()
        for sort_option in args:
            if sort_option.startswith('-'):
                sort_order = 'desc'
                sort_option = sort_option.lstrip('-')
            else:
                sort_order = 'asc'
            qs_copy.sort_options.append('%s %s' % (sort_option, sort_order))

        return qs_copy

    def query(self, **kwargs):
        """Return a new SolrQuerySet with the results populated from Solr.
        Any options passed in via keyword arguments take precedence
        over query options on the queryset.
        """
        qs_copy = self._clone()
        qs_copy.get_results(**kwargs)
        return qs_copy

    def all(self):
        """Return a new queryset that is a copy of the current one."""
        return self._clone()

    def none(self):
        """Return an empty result list."""
        qs_copy = self._clone()
        # replace any search queries with this to find not anything
        qs_copy.search_qs = ['NOT *:*']
        return qs_copy

    def _clone(self):
        """
        Return a copy of the current QuerySet for modification via
        filters.
        """
        # create a new instance with same solr and query opts
        # use current class to support extending
        qs_copy = self.__class__(solr=self.solr)
        # set attributes that can be copied directly
        qs_copy.start = self.start
        qs_copy.stop = self.stop

        # set copies of list attributes
        qs_copy.search_qs = list(self.search_qs)
        qs_copy.filter_qs = list(self.filter_qs)
        qs_copy.sort_options = list(self.sort_options)

        return qs_copy

    def set_limits(self, start, stop):
        """Return a subsection of the results, to support slicing."""
        if start is None:
            start = 0
        self.start = start
        self.stop = stop

    iter_chunk_size = 1000

    def __iter__(self):
        """Iterate over result documents for this query."""
        return iter(self.get_results())

    def __bool__(self):
        """results are not empty"""
        return bool(self.get_results())

    def __getitem__(self, k):
        """Return a single result or a slice of results"""
        # based on django queryset logic

        if not isinstance(k, (int, slice)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0)) or
                (isinstance(k, slice) and (k.start is None or k.start >= 0) and
                 (k.stop is None or k.stop >= 0))), \
            "Negative indexing is not supported."

        # if the result cache is already populated,
        # return the requested index or slice
        if self._result_cache is not None:
            return self._result_cache['response']['docs'][k]

        qs_copy = self._clone()

        if isinstance(k, slice):
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None

            qs_copy.set_limits(start, stop)
            return list(qs_copy)[::k.step] if k.step else qs_copy

        # single item
        qs_copy.set_limits(k, k + 1)
        return qs_copy.get_results()[0]
