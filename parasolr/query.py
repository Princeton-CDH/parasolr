"""
Object-oriented approach to Solr searching and filtering modeled
on :class:`django.models.queryset.QuerySet`.  Supports iteration,
slicing, counting, and boolean check to see if a search has results.

Filter, search and sort methods return a new queryset, and can be
chained. For example::

    SolrQuerySet(solrclient).filter(item_type='person') \
                            .search(name='hem*') \
                            .order_by('sort_name') \


If you are working with Django you should use
:class:`parasolr.django.SolrQuerySet`,
which will automatically initialize a new :class:`parasolr.django.SolrClient`
if one is not passed in.
"""

from typing import Dict, List

from parasolr.solr import SolrClient


class SolrQuerySet:
    """A Solr queryset object that allows for object oriented
    searching and filtering of Solr results. Allows search results
    to be pagination using slicing, count, and iteration.

    """

    _result_cache = None
    start = 0
    stop = None
    sort_options = []
    search_qs = []
    filter_qs = []
    field_list = []
    highlight_field = None
    highlight_opts = {}

    #: by default, combine search queries with AND
    default_search_operator = 'AND'

    def __init__(self, solr: SolrClient):
        # requires solr client so that this version can be django-agnostic
        self.solr = solr
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

        if self.field_list:
            query_opts['fl'] = ','.join(self.field_list)

        if self.highlight_field:
            query_opts.update({
                'hl': True,
                'hl.field': self.highlight_field
            })
            for key, val in self.highlight_opts.items():
                query_opts['hl.%s' % key] = val

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
        Multiple filters can be combined either in a single
        method call, or they can be chained for the same effect.
        For example::

            queryset.filter(item_type='person').filter(birth_year=1900)
            queryset.filter(item_type='person', birth_year=1900)

        To provide a filter that should be used in modified, provide
        the exact string of your filter query::

            queryset.filter('birth_year:[1800 TO *]')

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

    def only(self, *args, **kwargs):
        """Use field limit option to return only the specified fields.
        Optionally provide aliases for them in the return. Example::

            queryset.only('title', 'author', 'date')
            queryset.only('title:title_t', 'date:pubyear_i')

        """
        qs_copy = self._clone()
        qs_copy.field_list.extend(args)
        for key, value in kwargs.items():
            qs_copy.field_list.append('%s:%s' % (key, value))

        return qs_copy

    def highlight(self, field: str, **kwargs):
        """"Configure highlighting. Takes arbitrary Solr highlight
        parameters and adds the `hl.` prefix to them.  Example use::

            queryset.highlight('content', snippets=3, method='unified')
        """
        qs_copy = self._clone()
        qs_copy.highlight_field = field
        qs_copy.highlight_opts = kwargs
        return qs_copy

    def get_highlighting(self):
        """Return the highlighting portion of the Solr response."""
        if not self._result_cache:
            self.get_results()
        return self._result_cache.get('highlighting', {})

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
        qs_copy.highlight_field = self.highlight_field

        # set copies of list attributes
        qs_copy.search_qs = list(self.search_qs)
        qs_copy.filter_qs = list(self.filter_qs)
        qs_copy.sort_options = list(self.sort_options)
        qs_copy.field_list = list(self.field_list)
        qs_copy.highlight_opts = dict(self.highlight_opts)

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
