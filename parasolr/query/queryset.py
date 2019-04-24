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
import re
from typing import Any, Dict, List

from parasolr.solr import SolrClient
from parasolr.solr.client import QueryResponse


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
    facet_field_list = []
    range_facet_fields = []
    facet_opts = {}
    highlight_opts = {}
    raw_params = {}

    #: by default, combine search queries with AND
    default_search_operator = 'AND'

    #: any value constant
    ANY_VALUE = '[* TO *]'
    #: lookup separator
    LOOKUP_SEP = '__'

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
        self._result_cache = self.solr.query(**query_opts)
        return [doc.as_dict() for doc in self._result_cache.docs]

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

        if self.facet_field_list or self.range_facet_fields:
            query_opts.update({
                'facet': True,
                'facet.field': self.facet_field_list,
                'facet.range': self.range_facet_fields
            })
            for key, val in self.facet_opts.items():
                # use key as is if it starts with "f."
                # (field-specific facet options); otherwise prepend "facet."
                query_opts[key if key.startswith('f.') else 'facet.%s' % key] = val

        # include any raw query parameters
        query_opts.update(self.raw_params)

        return query_opts

    def count(self) -> int:
        """Total number of results for the current query"""

        # if result cache is already populated, use it
        if self._result_cache is not None:
            return self._result_cache.numFound

        # otherwise, query with current options but request zero rows
        # and do not populate the result cache
        query_opts = self.query_opts()
        # setting these by dictionary assignment, because conflicting
        # kwargs results in a Python exception
        query_opts['rows'] = 0
        query_opts['facet'] = False
        query_opts['hl'] = False
        return self.solr.query(**query_opts).numFound

    def get_facets(self) -> Dict[str, Dict]:
        """Return a dictionary of facet information included in the
        Solr response. Includes facet fields, facet ranges, etc. Facet
        field results are returned as an ordered dict of value and count.
        """
        if self._result_cache is not None:
            # wrap to process facets and return as dictionary
            # for Django template support
            qr = QueryResponse(self._result_cache)
            # NOTE: using dictionary syntax preserves OrderedDict
            return qr.facet_counts
        # since we just want a dictionary of facet fields, don't populate
        # the result cache, no rows needed

        query_opts = self.query_opts()
        query_opts['rows'] = 0
        query_opts['hl'] = False
        # setting these by dictionary assignment, because conflicting
        # kwargs results in a Python exception
        return self.solr.query(**query_opts).facet_counts

    @staticmethod
    def _lookup_to_filter(key: str, value: Any, tag: str='') -> str:
        """Convert keyword/value argument, with optional lookups separated by
        ``__``, including: in and exists. Field names should *NOT* include
        double-underscores by convention. Accepts an optional tag argument
        to specify an exclude tag as needed.

            Returns: A propertly formatted Solr query string.
        """
        # check for a lookup separator and split
        lookup = None
        solr_query = ''

        # split once on lookup separator; assumes only one
        split_key = key.split(SolrQuerySet.LOOKUP_SEP, 1)
        if len(split_key) == 1:
            # simple lookup, return key,value pair
            solr_query = '%s:%s' % (key, value)

        else:
            key, lookup = split_key

            # list filter (field__in=[a, b, c])
            if lookup == 'in':
                # value is a list, join with OR logic for all values in list,
                # treat '' or None values as flagging an exists query
                not_exists = '' in value or None in value
                value = list(filter(lambda x: x not in ['', None], value))

                # if we have a case where the list was just a single falsy value
                # treat as if __exists=False
                if not value:
                    solr_query = '-%s:%s' % (key, SolrQuerySet.ANY_VALUE)
                # otherwise, field lookup on any value by OR
                else:
                    # FIXME: do we need quotes around strings here?
                    solr_query = '%s:(%s)' % (key, ' OR '.join(value))

                    if not_exists:
                        # To search for no value OR specified values,
                        # do a negative lookup that negates a positive lookup
                        # for any value and double-negates a lookup
                        # for the requested values
                        # The final output is something like:
                        # -(item_type:[* TO *] OR item_type:(book OR periodical))
                        solr_query = '-(%s:%s OR -%s)' % \
                            (key, SolrQuerySet.ANY_VALUE, solr_query)

            # exists=True/False filter
            elif lookup == 'exists':
                # query for any value if exists is true; otherwise no value
                solr_query = '%s%s:%s' %  \
                    ('' if value else '-', key, SolrQuerySet.ANY_VALUE)

            elif lookup == 'range':
                start, end = value
                solr_query = '%s:[%s TO %s]' % (key, start or '*', end or '*')

        # format tag for inclusion and add to query if set
        if tag:
            solr_query = '{!tag=%s}%s' % (tag, solr_query)

        return solr_query

    def filter(self, *args, tag: str='', **kwargs) -> 'SolrQuerySet':
        """
        Return a new SolrQuerySet with Solr filter queries added.
        Multiple filters can be combined either in a single
        method call, or they can be chained for the same effect.
        For example::

            queryset.filter(item_type='person').filter(birth_year=1900)
            queryset.filter(item_type='person', birth_year=1900)

        A tag may be specified for the filter to be used with facet.field
        exclusions::

            queryset.filter(item_type='person', tag='person')

        To provide a filter that should be used unmodified, provide
        the exact string of your filter query::

            queryset.filter('birth_year:[1800 TO *]')

        You can also search for pre-defined using lookups on a field,
        for example::

            queryset.filter(item_type__in=['person', 'book'])
            queryset.filter(item_type__exists=False)

        Currently supported field lookups:

            * **in** : takes a list of values; supports '' or None to match
              on field not set
            * **exists**: boolean filter to look for any value / no value
            * **range**: range query. Takes a list or tuple of two values
               for the start and end of the range. Either value can
               be unset for an open-ended range (e.g. `year__range=(1800, None)`)

        """
        qs_copy = self._clone()

        # any args are treated as filter queries without modification
        qs_copy.filter_qs.extend(args)
        for key, value in kwargs.items():
            qs_copy.filter_qs.append(self._lookup_to_filter(key, value, tag=tag))
        return qs_copy

    def facet(self, *args: str, **kwargs) -> 'SolrQuerySet':
        """
        Request facets for specified fields. Returns a new SolrQuerySet
        with Solr faceting enabled and facet.field parameter set. Does not
        support ranged faceting.

        Subsequent calls will reset the facet.field to the last set of
        args in the chain.

        For example::

            qs = queryset.facet('person_type', 'age')
            qs = qs.facet('item_type')

        would result in `item_type` being the only facet field.
        """
        qs_copy = self._clone()

        # cast args tuple to list for consistency with other iterable fields
        qs_copy.facet_field_list = list(args)
        # add other kwargs to be prefixed in query_opts
        qs_copy.facet_opts.update(kwargs)

        return qs_copy

    def facet_field(self, field: str, exclude: str='', **kwargs) -> 'SolrQuerySet':
        """
        Request faceting for a single field. Returns a new SolrQuerySet
        with Solr faceting enabled and the field added to
        the list of facet fields. Any keyword arguments will be set
        as field-specific facet configurations.

        ``ex`` will specify a related filter query tag to exclude when
        generating counts for the facet.

        """
        qs_copy = self._clone()
        # append exclude tag if specified
        qs_copy.facet_field_list.append('{!ex=%s}%s' % (exclude, field)
                                        if exclude else field)
        # prefix any keyword args with the field name
        # (facet. prefix added in query_opts)

        qs_copy.facet_opts.update({
            'f.%s.facet.%s' % (field, opt) : value
            for opt, value in kwargs.items()})

        return qs_copy

    def facet_range(self, field: str, **kwargs) -> 'SolrQuerySet':
        """
        Request range faceting for a single field. Returns a new SolrQuerySet
        with Solr range faceting enabled and the field added to
        the list of facet fields. Keyword arguments such as start, end, and gap
        will be set as field-specific facet configurations.
        """
        # start, end, gap are required by Solr, but we don't actually
        # treat them any differently so it's easier to include as kwargs
        qs_copy = self._clone()
        # add field to list of range facet fields
        qs_copy.range_facet_fields.append(field)

        # configure facet options for this field (start, end, gap)
        qs_copy.facet_opts.update({
            'f.%s.facet.range.%s' % (field, opt) : value
            for opt, value in kwargs.items()})
        return qs_copy

    def search(self, *args, **kwargs) -> 'SolrQuerySet':
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

    def order_by(self, *args) -> 'SolrQuerySet':
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

    def query(self, **kwargs) -> 'SolrQuerySet':
        """Return a new SolrQuerySet with the results populated from Solr.
        Any options passed in via keyword arguments take precedence
        over query options on the queryset.
        """
        qs_copy = self._clone()
        qs_copy.get_results(**kwargs)
        return qs_copy

    def only(self, *args, replace=True, **kwargs) -> 'SolrQuerySet':
        """Use field limit option to return only the specified fields.
        Optionally provide aliases for them in the return. Subsequent
        calls will *replace* any previous field limits. Example::

            queryset.only('title', 'author', 'date')
            queryset.only('title:title_t', 'date:pubyear_i')

        """
        qs_copy = self._clone()
        # *replace* any existing field list with the current values
        if replace:
            qs_copy.field_list = list(args)
        # unless specified, in which case append
        else:
            qs_copy.field_list.extend(list(args))

        for key, value in kwargs.items():
            qs_copy.field_list.append('%s:%s' % (key, value))

        return qs_copy

    def also(self, *args, **kwargs) -> 'SolrQuerySet':
        """Use field limit option to return the specified fields,
        optionally provide aliases for them in the return. Works
        exactly the same way as :meth:`only` except that it
        does not any previously specified field limits.
        """
        return self.only(*args, replace=False, **kwargs)

    def highlight(self, field: str, **kwargs) -> 'SolrQuerySet':
        """"Configure highlighting. Takes arbitrary Solr highlight
        parameters and adds the `hl.` prefix to them.  Example use::

            queryset.highlight('content', snippets=3, method='unified')
        """
        qs_copy = self._clone()
        qs_copy.highlight_field = field
        qs_copy.highlight_opts = kwargs
        return qs_copy

    def raw_query_parameters(self, **kwargs) -> 'SolrQuerySet':
        """Add abritrary raw parameters to be included in the query
        request, e.g. for variables referenced in join or field queries.
        Analogous to the input of the same name in the Solr web interface."""
        qs_copy = self._clone()
        qs_copy.raw_params.update(kwargs)
        return qs_copy

    def get_highlighting(self):
        """Return the highlighting portion of the Solr response."""
        if not self._result_cache:
            self.get_results()
        return self._result_cache.get('highlighting', {})

    def all(self) -> 'SolrQuerySet':
        """Return a new queryset that is a copy of the current one."""
        return self._clone()

    def none(self) -> 'SolrQuerySet':
        """Return an empty result list."""
        qs_copy = self._clone()
        # replace any search queries with this to find not anything
        qs_copy.search_qs = ['NOT *:*']
        return qs_copy

    def _clone(self) -> 'SolrQuerySet':
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

        # set copies of list and dict attributes
        qs_copy.search_qs = list(self.search_qs)
        qs_copy.filter_qs = list(self.filter_qs)
        qs_copy.sort_options = list(self.sort_options)
        qs_copy.field_list = list(self.field_list)
        qs_copy.range_facet_fields = list(self.range_facet_fields)
        qs_copy.highlight_opts = dict(self.highlight_opts)
        qs_copy.raw_params = dict(self.raw_params)
        qs_copy.facet_field_list = list(self.facet_field_list)
        qs_copy.facet_opts = dict(self.facet_opts)

        return qs_copy

    def set_limits(self, start, stop):
        """Set limits to get a subsection of the results, to support slicing."""
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
            return self._result_cache.docs[k]

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
