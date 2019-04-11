from collections import OrderedDict
from unittest.mock import patch, Mock

import pytest

from parasolr.solr import SolrClient
from parasolr.solr.client import QueryResponse, ParasolrDict
from parasolr.query import SolrQuerySet


class TestSolrQuerySet:

    def test_init(self):
        # use solr client if passed in
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        assert sqs.solr == mocksolr

    def test_query_opts(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)

        # default behavior: find all starting at 0
        query_opts = sqs.query_opts()
        assert query_opts['start'] == 0
        assert query_opts['q'] == '*:*'
        # don't include unset options
        for opt in ['fq', 'rows', 'sort', 'fl', 'hl', 'hl.field', 'facet']:
            assert opt not in query_opts

        # customized query opts
        sqs.start = 10
        sqs.stop = 20
        sqs.sort_options = ['title asc', 'date desc']
        sqs.filter_qs = ['item_type:work']
        sqs.search_qs = ['title:reading', 'author:johnson']
        sqs.field_list = ['title', 'author', 'date:pubyear_i']
        sqs.highlight_field = 'content'
        sqs.highlight_opts = {'snippets': 3, 'method': 'unified'}
        sqs.facet_field = ['item_type', 'member_type']
        sqs.facet_opts = {'sort': 'count'}
        query_opts = sqs.query_opts()

        assert query_opts['start'] == sqs.start
        assert query_opts['rows'] == sqs.stop - sqs.start
        assert query_opts['fq'] == sqs.filter_qs
        assert query_opts['q'] == ' AND '.join(sqs.search_qs)
        assert query_opts['sort'] == ','.join(sqs.sort_options)
        assert query_opts['fl'] == ','.join(sqs.field_list)
        # highlighting should be turned on
        assert query_opts['hl']
        assert query_opts['hl.field'] == 'content'
        # highlighting options added with hl.prefix
        assert query_opts['hl.snippets'] == 3
        assert query_opts['hl.method'] == 'unified'
        # make sure faceting opts are preserved
        assert query_opts['facet'] is True
        assert query_opts['facet.field'] == sqs.facet_field
        assert query_opts['facet.sort'] == 'count'

    def test_query(self):
        mocksolr = Mock(spec=SolrClient)
        mocksolr.query.return_value.docs = []
        sqs = SolrQuerySet(mocksolr)
        query_sqs = sqs.query()
        # returns a copy, not same queryset
        assert query_sqs != sqs
        # sets the result cache (via get_results)
        assert query_sqs._result_cache
        # result cache not set on original
        assert not sqs._result_cache


    def test_get_results(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)

        mockresponse = Mock()
        mockresponse.docs = [
            ParasolrDict({'a': 1})
        ]
        mocksolr.query.return_value = mockresponse

        # by default, should query solr with options from query_opts
        # and wrap = false
        query_opts = sqs.query_opts()
        assert sqs.get_results() == mockresponse.docs
        assert sqs._result_cache == mockresponse
        mocksolr.query.assert_called_with(**query_opts)

        # parameters passed in take precedence
        local_opts = {'q': 'name:hemingway', 'sort': 'name asc'}
        sqs.get_results(**local_opts)
        # update copy of query opts with locally passed in params
        query_opts.update(local_opts)
        mocksolr.query.assert_called_with(**query_opts)

    def test_count(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)

        # simulate result cache already populated; should use
        sqs._result_cache = Mock()
        sqs._result_cache.numFound = 5477
        assert sqs.count() == 5477
        mocksolr.query.assert_not_called()

        # if cache is not populated, should query for count
        sqs._result_cache = None
        mocksolr.query.return_value = Mock()
        mocksolr.query.return_value.numFound = 343
        assert sqs.count() == 343
        count_query_opts = sqs.query_opts()
        count_query_opts['rows'] = 0
        count_query_opts['hl'] = False
        count_query_opts['facet'] = False
        mocksolr.query.assert_called_with(**count_query_opts)
        # cache should not be populated
        assert not sqs._result_cache

    @patch('parasolr.query.QueryResponse')
    def test_get_facets(self, mockQR):
        mocksolr = Mock(spec=SolrClient)
        # mock cached solr response
        mock_response = Mock()
        sqs = SolrQuerySet(mocksolr)
        # mock out return of MockQR constructor to ensure it calls
        # facet_counts.facet_fields
        mockQR.return_value = Mock()
        mockQR.return_value.facet_counts = {'facet_fields': OrderedDict(a=1)}
        sqs._result_cache = mock_response

        ret = sqs.get_facets()
        # QueryResponse called to wrap mock_response
        assert mockQR.called
        # called with the cached response
        mockQR.assert_called_with(mock_response)
        # casts return to an OrderedDict
        assert isinstance(ret, OrderedDict)
        # return the value of facet_counts.facet_fields
        assert ret == OrderedDict(a=1)

        # now test no cached result
        mocksolr.query.return_value = Mock()
        mocksolr.query.return_value.facet_counts = {'facet_fields': OrderedDict(b=2)}
        sqs._result_cache = None
        # clear the previous mocks
        mockQR.reset_mock()

        ret = sqs.get_facets()
        # QueryResponse not called to wrap return of query
        assert not mockQR.called
        # solr.query called
        assert mocksolr.query.called
        # should be called with rows=0 and hl=False to avoid inefficiencies
        name, args, kwargs = mocksolr.query.mock_calls[0]
        assert kwargs['rows'] == 0
        assert not kwargs['hl']
        # casts return to an OrderedDict
        assert isinstance(ret, OrderedDict)
        # return should be the return value of facet_counts.facet_fields
        assert ret == OrderedDict(b=2)

    def test_filter(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)

        # arg options added to filter list as is
        new_filters = ['item_type:work', 'date:[1550 TO 1900]']
        filtered_qs = sqs.filter(*new_filters)
        # returned queryset has the filters
        assert filtered_qs.filter_qs == new_filters
        # original queryset is unchanged
        assert not sqs.filter_qs

        # keyword arg options converted into filters
        filtered_qs = sqs.filter(item_type='work', date=1500)
        # returned queryset has the filters
        assert 'item_type:work' in filtered_qs.filter_qs
        assert 'date:1500' in filtered_qs.filter_qs
        # original queryset is unchanged
        assert not sqs.filter_qs

        # chaining adds to the filters
        filtered_qs = sqs.filter(item_type='work').filter(date=1500) \
                         .filter('name:he*')
        assert 'item_type:work' in filtered_qs.filter_qs
        assert 'date:1500' in filtered_qs.filter_qs
        assert 'name:he*' in filtered_qs.filter_qs

    def test_facet(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        # facet a search
        facet_list = ['person_type', 'item_type']
        faceted_qs = sqs.facet(*facet_list)
        # faceting should be set on
        assert faceted_qs.facet_field == facet_list
        # facet opts and field for original queryset should be unchanged
        assert not sqs.facet_opts
        assert not sqs.facet_field

        # a call to another method should leave facet options as is
        faceted_qs = faceted_qs.filter(foo='bar')
        assert faceted_qs.facet_field== facet_list
        # subsequents calls to facet should simply reset list
        facet_list = ['foobars']
        faceted_qs = faceted_qs.facet(*facet_list)
        assert faceted_qs.facet_field == facet_list
        # kwargs should simply be set in facet opts
        faceted_qs = faceted_qs.facet(*facet_list, sort='count')
        assert faceted_qs.facet_field == facet_list
        assert faceted_qs.facet_opts['sort'] == 'count'

    def test_search(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)

        # arg options added to filter list as is
        queries = ['item_type:work', 'date:[1550 TO *]']
        search_sqs = sqs.search(*queries)
        # returned queryset has the filters
        assert search_sqs.search_qs == queries
        # original queryset is unchanged
        assert not sqs.search_qs

        # keyword arg options are converted
        search_sqs = sqs.search(item_type='work', date=1550)
        assert 'item_type:work' in search_sqs.search_qs
        assert 'date:1550' in search_sqs.search_qs
        # original queryset is unchanged
        assert not sqs.search_qs

        # chaining is additive
        search_sqs = sqs.search(item_type='work').search(date=1550)
        assert 'item_type:work' in search_sqs.search_qs
        assert 'date:1550' in search_sqs.search_qs
        # original queryset is unchanged
        assert not sqs.search_qs

    def test_order_by(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)

        # default is ascending
        sorted_sqs = sqs.order_by('date')
        assert sorted_sqs.sort_options == ['date asc']
        # original queryset is unchanged
        assert not sqs.sort_options

        # - indicates descending
        sorted_sqs = sqs.order_by('-date')
        assert sorted_sqs.sort_options == ['date desc']
        # original queryset is unchanged
        assert not sqs.sort_options

        # can handle multiple
        sorted_sqs = sqs.order_by('title', 'date')
        assert sorted_sqs.sort_options == ['title asc', 'date asc']
        # original queryset is unchanged
        assert not sqs.sort_options

        # chaining works the same way
        sorted_sqs = sqs.order_by('title').order_by('date')
        assert sorted_sqs.sort_options == ['title asc', 'date asc']
        # original queryset is unchanged
        assert not sqs.sort_options

    def test_only(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        only_fields = ['title', 'author', 'date']
        # field name only, single list
        fields_sqs = sqs.only(*only_fields)
        # field list refined
        assert fields_sqs.field_list == only_fields
        # original field list unchanged
        assert not sqs.field_list

        # chaining is not equivalent, but *replaces*
        fields_sqs = sqs.only('title').only('author')
        # field list refined
        assert fields_sqs.field_list == ['author']
        # original field list unchanged
        assert not sqs.field_list

        # only with field alias
        fields_sqs = sqs.only(title='title_i')
        assert 'title:title_i' in fields_sqs.field_list

    def test_highlight(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        # field only, defaults
        highlight_qs = sqs.highlight('content')
        assert highlight_qs.highlight_field == 'content'
        assert highlight_qs.highlight_opts == {}
        # original unchanged
        assert sqs.highlight_field is None

        # field and opts
        highlight_qs = sqs.highlight('text', snippets=3, method='unified')
        assert highlight_qs.highlight_field == 'text'
        assert highlight_qs.highlight_opts == \
            {'snippets': 3, 'method': 'unified'}
        # original unchanged
        assert sqs.highlight_field is None
        assert sqs.highlight_opts == {}

    def test_raw_query_parameters(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        raw_q = {'extra_query': 'foobar'}
        raw_sqs = sqs.raw_query_parameters(**raw_q)
        # raw query stored
        assert raw_sqs.raw_params == raw_q
        # included in query opts
        assert raw_q['extra_query'] in raw_sqs.query_opts()['extra_query']
        # original unchanged
        assert sqs.raw_params == {}

        # additional raw params add rather than replace
        rawer_sqs = raw_sqs.raw_query_parameters(another='two')
        assert len(rawer_sqs.raw_params) == 2

    def test_get_highlighting(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        # simulate result cache already populated, no highlighting
        sqs._result_cache = {'response': {'docs': []}}
        assert sqs.get_highlighting() == {}

        # simulate response with highlighting
        mock_highlights = {'id1': {'text': ['sample match content']}}
        sqs._result_cache = {'highlighting': mock_highlights}
        assert sqs.get_highlighting() == mock_highlights

        # should populate cache if empty
        sqs._result_cache = None
        with patch.object(sqs, 'get_results') as mock_get_results:
            def set_result_cache():
                sqs._result_cache = Mock()
            mock_get_results.side_effect = set_result_cache

            sqs.get_highlighting()
            mock_get_results.assert_called_with()

    def test_all(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        # all just calls clone and returns the queryset copy
        with patch.object(sqs, '_clone') as mockclone:
            all_sqs = sqs.all()
            mockclone.assert_called_with()
            assert all_sqs == mockclone.return_value

    def test_none(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        none_sqs = sqs.none()
        # new queryset search replaced with something to return nothing
        assert none_sqs.search_qs == ['NOT *:*']
        # original queryset unchanged
        assert sqs.search_qs == []

        # none after search terms replaces the search
        search_sqs = SolrQuerySet(mocksolr).search('item_type:work')
        none_sqs = search_sqs.none()
        assert search_sqs.search_qs == ['item_type:work']
        assert none_sqs.search_qs == ['NOT *:*']

    def test__clone(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        # clone default with no filters
        cloned_sqs = sqs._clone()
        assert cloned_sqs.start == 0
        assert cloned_sqs.stop is None
        assert cloned_sqs.search_qs == []
        assert cloned_sqs.filter_qs == []
        assert cloned_sqs.sort_options == []

        # set everything
        custom_sqs = sqs.filter(item_type='person').search(name='he*') \
                        .order_by('birth_year')
        custom_sqs.set_limits(10, 100)
        custom_clone = custom_sqs._clone()
        assert custom_clone.start == 10
        assert custom_clone.stop == 100
        # list fields should be equal but not be the same object
        assert custom_clone.search_qs == custom_sqs.search_qs
        assert not custom_clone.search_qs is custom_sqs.search_qs
        assert custom_clone.filter_qs == custom_sqs.filter_qs
        assert not custom_clone.filter_qs is custom_sqs.filter_qs
        assert custom_clone.sort_options == custom_sqs.sort_options
        assert not custom_clone.sort_options is custom_sqs.sort_options

        # subclass clone should return subclass

        class CustomSolrQuerySet(SolrQuerySet):
            pass

        custom_clone = CustomSolrQuerySet(mocksolr)._clone()
        assert isinstance(custom_clone, CustomSolrQuerySet)

        # sanity-check chaining
        sqs = SolrQuerySet(mocksolr)
        filtered_sqs = sqs.filter(item_type='person')
        # filter should be set
        assert 'item_type:person' in filtered_sqs.filter_qs
        sorted_sqs = filtered_sqs.order_by('birth_year')
        # sort and filter should be set
        assert 'item_type:person' in sorted_sqs.filter_qs
        assert 'birth_year asc' in sorted_sqs.sort_options
        search_sqs = sorted_sqs.search(name='hem*')
        # search , sort, and filter should be set
        assert 'item_type:person' in search_sqs.filter_qs
        assert 'birth_year asc' in search_sqs.sort_options
        assert 'name:hem*' in search_sqs.search_qs

    def test__lookup_to_filter(self):
        assert SolrQuerySet._lookup_to_filter('item_type', 'work') == \
            'item_type:work'

    def test_iter(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        with patch.object(sqs, 'get_results') as mock_get_results:
            mock_get_results.return_value = [{'id': 1}, {'id': 2}]
            results_iterator = sqs.__iter__()
            # not sure how best to test iterator...
            assert list(results_iterator) == mock_get_results.return_value
            mock_get_results.assert_called_with()

        # TODO: test iterating over a slice?

    def test_bool(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        with patch.object(sqs, 'get_results') as mock_get_results:
            # with results
            mock_get_results.return_value = [{'id': 1}, {'id': 2}]
            assert sqs

            # with no results
            mock_get_results.return_value = []
            assert not sqs

    def test_set_limits(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)
        sqs.set_limits(10, 50)
        assert sqs.start == 10
        assert sqs.stop == 50

        sqs.set_limits(None, None)
        assert sqs.start == 0
        assert sqs.stop is None

    def test_get_item(self):
        mocksolr = Mock(spec=SolrClient)
        sqs = SolrQuerySet(mocksolr)

        # simulate result cache already populated
        sqs._result_cache = Mock()
        sqs._result_cache.docs = [1, 2, 3, 4, 5]
        # single item
        assert sqs[0] == 1
        assert sqs[1] == 2
        # slice
        assert sqs[0:2] == [1, 2]
        # slice with step
        assert sqs[1:5:2] == [2, 4]

        # simulate result cache *not* populated
        sqs._result_cache = None
        # - slice
        sliced_qs = sqs[10:20]
        assert isinstance(sliced_qs, SolrQuerySet)
        assert sliced_qs.start == 10
        assert sliced_qs.stop == 20
        # - slice with implicit start
        sliced_qs = sqs[:5]
        assert isinstance(sliced_qs, SolrQuerySet)
        assert sliced_qs.start == 0
        assert sliced_qs.stop == 5
        # - slice with implicit end
        sliced_qs = sqs[3:]
        assert isinstance(sliced_qs, SolrQuerySet)
        assert sliced_qs.start == 3
        assert sliced_qs.stop is None

        # - slice with step - requires fetching results
        with patch.object(sqs, '_clone') as mock_clone:
            # for step slicing, calls list on the cloned queryset,
            # which calls iterate; supply list of numbers as response
            mock_clone.return_value.__iter__.return_value = range(20)
            sliced_qs = sqs[0:10:2]
            assert not isinstance(sliced_qs, SolrQuerySet)
            assert sliced_qs[1] == 2
            assert sliced_qs[-1] == 18

        # - single item
        with patch.object(sqs, '_clone') as mock_clone:
            mock_clone.return_value.get_results.return_value \
                = ['d']
            item = sqs[3]

            mock_clone.assert_called_with()
            mock_clone.return_value.set_limits.assert_called_with(3, 4)
            mock_clone.return_value.get_results.assert_called_with()
            assert item == 'd'

        # handle invalid input
        with pytest.raises(TypeError):
            assert sqs['foo']

        with pytest.raises(AssertionError):
            assert sqs[-1]

        with pytest.raises(AssertionError):
            assert sqs[:-1]
