from unittest import TestCase
from unittest.mock import Mock, patch

from parasolr.query import AliasedSolrQuerySet



class MyAliasedSolrQuerySet(AliasedSolrQuerySet):
    """extended version of AliasedSolrQuerySet for testing"""

    #: map app/readable field names to actual solr fields
    field_aliases = {
        'name': 'name_t',
        'year':'year_i',
        'has_info':'has_info_b',
    }

class TestAliasedSolrQuerySet(TestCase):

    def setUp(self):
        self.mysqs = MyAliasedSolrQuerySet(solr=Mock())

    def test_init(self):
        """field list should be populated from field aliases on init"""
        assert self.mysqs.field_list
        assert len(self.mysqs.field_list) == len(MyAliasedSolrQuerySet.field_aliases.keys())
        for key, val in self.mysqs.field_aliases.items():
            assert '%s:%s' % (key, val) in self.mysqs.field_list

    def test_unalias_args(self):
        """list of aliased args should be converted to solr field"""
        unaliased_args = self.mysqs._unalias_args('name', 'year', 'foo')
        # lookup from field aliases
        assert self.mysqs.field_aliases['name'] in unaliased_args
        assert self.mysqs.field_aliases['year'] in unaliased_args
        # if not present - used unchanged
        assert 'foo' in unaliased_args

    def test_unalias_kwargs(self):
        """keys in keyword arguments should be converted to solr field name"""
        unaliased_kwargs = self.mysqs._unalias_kwargs(name='Jane', year=1942, foo='bar')
        # keys converted
        assert self.mysqs.field_aliases['name'] in unaliased_kwargs
        assert self.mysqs.field_aliases['year'] in unaliased_kwargs
        assert 'foo' in unaliased_kwargs
        # values unchanged
        assert unaliased_kwargs[self.mysqs.field_aliases['name']] == 'Jane'
        assert unaliased_kwargs['foo'] == 'bar'

    @patch('parasolr.query.queryset.SolrQuerySet.filter')
    def test_filter(self, mock_filter):
        # arg only - not modified
        self.mysqs.filter('name:foo')
        mock_filter.assert_called_with('name:foo', tag='')

        # keyworg arg should be unaliased
        self.mysqs.filter(name='Jane')
        mock_filter.assert_called_with(name_t='Jane', tag='')

        # keyworg arg with lookup should also be unaliased
        self.mysqs.filter(name__in=['Jane', 'Judy'])
        mock_filter.assert_called_with(name_t__in=['Jane', 'Judy'], tag='')

        # unknown field should be ignored
        self.mysqs.filter(tuesday='wednesday')
        mock_filter.assert_called_with(tuesday='wednesday', tag='')

        # should work with a tag
        self.mysqs.filter('foo:bar', name='Jane', tag='baz')
        mock_filter.assert_called_with('foo:bar', name_t='Jane', tag='baz')

    @patch('parasolr.query.queryset.SolrQuerySet.facet')
    def test_facet(self, mock_filter):
        # arg should be unaliased
        self.mysqs.facet('name')
        mock_filter.assert_called_with(self.mysqs.field_aliases['name'])

        # kwrags should be ignored
        self.mysqs.facet('name', missing=True)
        mock_filter.assert_called_with(self.mysqs.field_aliases['name'],
                                       missing=True)

    @patch('parasolr.query.queryset.SolrQuerySet.facet_field')
    def test_facet_field(self, mock_facet_field):
        # field name should be unaliased
        self.mysqs.facet_field('year')
        mock_facet_field.assert_called_with(self.mysqs.field_aliases['year'],
                                            exclude='')

        # work with exclude and other kwargs
        self.mysqs.facet_field('year', exclude=True, missing=True)
        mock_facet_field.assert_called_with(self.mysqs.field_aliases['year'],
                                            exclude=True, missing=True)

    @patch('parasolr.query.queryset.SolrQuerySet.order_by')
    def test_order_by(self, mock_order_by):
        # args should be unaliased
        self.mysqs.order_by('year')
        mock_order_by.assert_called_with(self.mysqs.field_aliases['year'])

    @patch('parasolr.query.queryset.SolrQuerySet.only')
    def test_only(self, mock_only):
        # args should be unaliased
        self.mysqs.only('name', 'year')
        mock_only.assert_called_with(self.mysqs.field_aliases['name'],
                                     self.mysqs.field_aliases['year'])

        # kwargs should be ignored
        self.mysqs.only(end_year_i='end_year')
        mock_only.assert_called_with(end_year_i='end_year')

    @patch('parasolr.query.queryset.SolrQuerySet.highlight')
    def test_highlight(self, mock_highlight):
        # args should be unaliased
        self.mysqs.highlight('name')
        mock_highlight.assert_called_with(self.mysqs.field_aliases['name'])
        # unknown should be ignored
        self.mysqs.highlight('foo_b')
        mock_highlight.assert_called_with('foo_b')
