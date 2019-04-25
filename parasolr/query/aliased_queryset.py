from typing import Dict

from parasolr.query.queryset import SolrQuerySet


class AliasedSolrQuerySet(SolrQuerySet):
    '''Extension of :class:`~parasolr.query.queryset.SolrQuerySet`
    with support for aliasing Solr fields to more readable versions
    for use in code. To use, extend this class and define a
    dictionary of :attr:`field_aliases` with the same syntax you would
    when calling :meth:`only`. Those field aliases will be set
    as the default initial value for :attr:`field_list`, and aliases
    can be used in all extended methods.
    '''

    #: map of application-specific, readable field names
    #: to actual solr fields (i.e. if using dynamic field types)
    field_aliases = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # set default field list based on field_aliases
        self.field_list = ['%s:%s' % (key, value)
                           for key, value in self.field_aliases.items()]

        # generate reverse lookup for updating facets & highlights
        self.reverse_aliases = {val: key for key, val in self.field_aliases.items()}

    def _unalias_args(self, *args):
        '''convert alias name to solr field for list of args'''
        return [self.field_aliases.get(arg, arg) for arg in args]

    def _unalias_kwargs(self, **kwargs):
        '''convert alias name to solr field for keys in kwargs'''
        return {self.field_aliases.get(key, key): val
                for key, val in kwargs.items()}

    def _unalias_kwargs_with_lookups(self, **kwargs):
        '''convert alias name to solr field for keys in kwargs
        with support for __ lookups for filters'''
        new_kwargs = {}
        for key, val in kwargs.items():
            field_parts = key.split(self.LOOKUP_SEP, 1)
            # first part is always present = field name
            field = field_parts[0]
            # get alias for key if there is one
            field = self.field_aliases.get(field, field)

            # if there is a lookup, add it back to the unaliased field
            if len(field_parts) > 1:
                field = '%s__%s' % (field, field_parts[1])
            new_kwargs[field] = val

        return new_kwargs

    def filter(self, *args, tag: str='', **kwargs) -> 'AliasedSolrQuerySet':
        '''Extend :meth:`parasolr.query.queryset.SolrQuerySet.filter`
        to support using aliased field names for keyword argument keys.'''
        kwargs = self._unalias_kwargs_with_lookups(**kwargs)
        return super().filter(*args, tag=tag, **kwargs)

    def facet(self, *args, **kwargs) -> 'AliasedSolrQuerySet':
        '''Extend :meth:`parasolr.query.queryset.SolrQuerySet.facet`
        to support using aliased field names in args.'''
        args = self._unalias_args(*args)
        return super().facet(*args, **kwargs)

    def facet_field(self, field: str, exclude: str='', **kwargs) -> 'AlaisedSolrQuerySet':
        '''Extend :meth:`parasolr.query.queryset.SolrQuerySet.facet_field``
        to support using aliased field names for field parameter.'''
        field = self.field_aliases.get(field, field)
        return super().facet_field(field, exclude=exclude, **kwargs)

    def order_by(self, *args) -> 'AliasedSolrQuerySet':
        '''Extend :meth:`parasolr.query.queryset.SolrQuerySet.order_by``
        to support using aliased field names in sort arguments.'''
        args = self._unalias_args(*args)
        return super().order_by(*args)

    def only(self, *args, **kwargs) -> 'AliasedSolrQuerySet':
        '''Extend :meth:`parasolr.query.queryset.SolrQuerySet.only``
        to support using aliased field names for args (but not kwargs).'''

        # convert args to aliased args, switching them to keyword
        # args; unknown fields are treated the same way
        kwargs.update({arg: self.field_aliases.get(arg, arg)
                       for arg in args})
        return super().only(**kwargs)

    # also method does not need to be extended, since it runs through only

    def highlight(self, field: str, **kwargs) -> 'AliasedSolrQuerySet':
        '''Extend :meth:`parasolr.query.queryset.SolrQuerySet.highlight``
        to support using aliased field names in kwargs.'''
        field = self.field_aliases.get(field, field)
        return super().highlight(field, **kwargs)

    def get_facets(self) -> Dict[str, int]:
        '''Extend :meth:`parasolr.query.queryset.SolrQuerySet.get_facets``
        to use aliased field names for facet and range facet keys.'''
        facets = super().get_facets()

        # replace field names in facet field and facet range
        # with aliased field names
        for section in ['facet_fields', 'facet_ranges']:
            facets[section] = {
                self.reverse_aliases.get(field, field): val
                for field, val in facets[section].items()
            }

        return facets

    # NOTE: may want to do the same for highlighting also eventually,
    # but no immediate need and it's structured differently so
    # not as obvious how to handle
