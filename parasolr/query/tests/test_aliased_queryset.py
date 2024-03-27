import copy
from unittest import TestCase
from unittest.mock import Mock, patch

from parasolr.query import AliasedSolrQuerySet


class MyAliasedSolrQuerySet(AliasedSolrQuerySet):
    """extended version of AliasedSolrQuerySet for testing"""

    #: map app/readable field names to actual solr fields
    field_aliases = {
        "name": "name_t",
        "year": "year_i",
        "has_info": "has_info_b",
    }


class TestAliasedSolrQuerySet(TestCase):
    def setUp(self):
        self.mysqs = MyAliasedSolrQuerySet(solr=Mock())

    def test_init(self):
        """field list should be populated from field aliases on init"""
        assert self.mysqs.field_list
        assert len(self.mysqs.field_list) == len(
            MyAliasedSolrQuerySet.field_aliases.keys()
        )
        for key, val in self.mysqs.field_aliases.items():
            assert "%s:%s" % (key, val) in self.mysqs.field_list

        # reverse lookup should be populated
        assert self.mysqs.reverse_aliases
        assert len(self.mysqs.reverse_aliases.keys()) == len(
            MyAliasedSolrQuerySet.field_aliases.keys()
        )
        assert self.mysqs.reverse_aliases["name_t"] == "name"

    def test_unalias_args(self):
        """list of aliased args should be converted to solr field"""
        unaliased_args = self.mysqs._unalias_args("name", "year", "foo")
        # lookup from field aliases
        assert self.mysqs.field_aliases["name"] in unaliased_args
        assert self.mysqs.field_aliases["year"] in unaliased_args
        # if not present - used unchanged
        assert "foo" in unaliased_args

    def test_unalias_kwargs(self):
        """keys in keyword arguments should be converted to solr field name"""
        unaliased_kwargs = self.mysqs._unalias_kwargs(name="Jane", year=1942, foo="bar")
        # keys converted
        assert self.mysqs.field_aliases["name"] in unaliased_kwargs
        assert self.mysqs.field_aliases["year"] in unaliased_kwargs
        assert "foo" in unaliased_kwargs
        # values unchanged
        assert unaliased_kwargs[self.mysqs.field_aliases["name"]] == "Jane"
        assert unaliased_kwargs["foo"] == "bar"

    @patch("parasolr.query.queryset.SolrQuerySet.filter")
    def test_filter(self, mock_filter):
        # arg only - not modified
        self.mysqs.filter("name:foo")
        mock_filter.assert_called_with("name:foo", tag="")

        # keyworg arg should be unaliased
        self.mysqs.filter(name="Jane")
        mock_filter.assert_called_with(name_t="Jane", tag="")

        # keyworg arg with lookup should also be unaliased
        self.mysqs.filter(name__in=["Jane", "Judy"])
        mock_filter.assert_called_with(name_t__in=["Jane", "Judy"], tag="")

        # unknown field should be ignored
        self.mysqs.filter(tuesday="wednesday")
        mock_filter.assert_called_with(tuesday="wednesday", tag="")

        # should work with a tag
        self.mysqs.filter("foo:bar", name="Jane", tag="baz")
        mock_filter.assert_called_with("foo:bar", name_t="Jane", tag="baz")

    @patch("parasolr.query.queryset.SolrQuerySet.search")
    def test_search(self, mock_search):
        # keyworg arg should be unaliased
        self.mysqs.search(name="Jane")
        mock_search.assert_called_with(name_t="Jane")

        # keyworg arg with lookup should also be unaliased
        self.mysqs.search(name__in=["Jane", "Judy"])
        mock_search.assert_called_with(name_t__in=["Jane", "Judy"])

        # unknown field should be ignored
        self.mysqs.search(tuesday="wednesday")
        mock_search.assert_called_with(tuesday="wednesday")

    @patch("parasolr.query.queryset.SolrQuerySet.facet")
    def test_facet(self, mock_filter):
        # arg should be unaliased
        self.mysqs.facet("name")
        mock_filter.assert_called_with(self.mysqs.field_aliases["name"])

        # kwrags should be ignored
        self.mysqs.facet("name", missing=True)
        mock_filter.assert_called_with(self.mysqs.field_aliases["name"], missing=True)

    @patch("parasolr.query.queryset.SolrQuerySet.stats")
    def test_stats(self, mock_stats):
        # args should be unaliasted
        self.mysqs.stats("year")
        mock_stats.assert_called_with(self.mysqs.field_aliases["year"])

        # kwargs should be passed as is
        self.mysqs.stats("year", calcdistinct=True)
        mock_stats.assert_called_with(
            self.mysqs.field_aliases["year"], calcdistinct=True
        )

    @patch("parasolr.query.queryset.SolrQuerySet.facet_field")
    def test_facet_field(self, mock_facet_field):
        # field name should be unaliased
        self.mysqs.facet_field("year")
        mock_facet_field.assert_called_with(
            self.mysqs.field_aliases["year"], exclude=""
        )

        # work with exclude and other kwargs
        self.mysqs.facet_field("year", exclude=True, missing=True)
        mock_facet_field.assert_called_with(
            self.mysqs.field_aliases["year"], exclude=True, missing=True
        )

    @patch("parasolr.query.queryset.SolrQuerySet.order_by")
    def test_order_by(self, mock_order_by):
        # args should be unaliased
        self.mysqs.order_by("year")
        mock_order_by.assert_called_with(self.mysqs.field_aliases["year"])

    @patch("parasolr.query.queryset.SolrQuerySet.only")
    def test_only(self, mock_only):
        # args should be unaliased
        self.mysqs.only("name", "year")
        mock_only.assert_called_with(
            name=self.mysqs.field_aliases["name"], year=self.mysqs.field_aliases["year"]
        )

        # field with no alias passed through as kwarg
        self.mysqs.only("foo")
        mock_only.assert_called_with(foo="foo")

        # kwargs should be ignored
        self.mysqs.only(end_year_i="end_year")
        mock_only.assert_called_with(end_year_i="end_year")

    @patch("parasolr.query.queryset.SolrQuerySet.highlight")
    def test_highlight(self, mock_highlight):
        # args should be unaliased
        self.mysqs.highlight("name")
        mock_highlight.assert_called_with(self.mysqs.field_aliases["name"])
        # unknown should be ignored
        self.mysqs.highlight("foo_b")
        mock_highlight.assert_called_with("foo_b")

    @patch("parasolr.query.queryset.SolrQuerySet.group")
    def test_group(self, mock_group):
        # args should be unaliased
        self.mysqs.group("name")
        mock_group.assert_called_with(self.mysqs.field_aliases["name"])
        # unknown should be ignored
        self.mysqs.group("foo_b")
        mock_group.assert_called_with("foo_b")

    @patch("parasolr.query.queryset.SolrQuerySet.get_facets")
    def test_get_facets(self, mock_get_facets):
        sample_facet_result = {
            "facet_fields": {
                "has_info_b": ["false", 5967, "true", 632],
                "other": ["false", 6, "true", 4],
            },
            "facet_ranges": {
                "year_i": {
                    "counts": ["1900", 100, "1920", 5939, "1940", 477, "1960", 6],
                    "gap": 20,
                    "start": 1900,
                    "end": 1980,
                },
                "birth": {
                    "counts": ["1900", 100, "1920", 5939, "1940", 477, "1960", 6],
                    "gap": 20,
                    "start": 1900,
                    "end": 1980,
                },
            },
        }
        mock_get_facets.return_value = sample_facet_result.copy()

        # known keys should be converted to alias
        facets = self.mysqs.get_facets()
        mock_get_facets.assert_called_with()
        # known field alias is updated
        assert "has_info" in facets["facet_fields"]
        assert (
            facets["facet_fields"]["has_info"]
            == sample_facet_result["facet_fields"]["has_info_b"]
        )
        # non-aliased field is ignored
        assert "other" in facets["facet_fields"]

        # range fields updated with aliases also
        assert "year" in facets["facet_ranges"]
        assert (
            facets["facet_ranges"]["year"]
            == sample_facet_result["facet_ranges"]["year_i"]
        )
        # non-aliased field is ignored
        assert "birth" in facets["facet_ranges"]

        # error on query returns empty facets
        mock_get_facets.return_value = {}
        assert self.mysqs.get_facets() == {}

    @patch("parasolr.query.queryset.SolrQuerySet.get_stats")
    def test_get_stats(self, mock_get_stats):
        sample_stats = {
            # In setup for tests, year_i is aliased to year and
            # start_i is unaliased
            "stats_fields": {
                "year_i": {"min": 1918.0, "max": 1998.0},
                "start_i": {
                    "min": 1919.0,
                    "max": 2020.0,
                },
            }
        }
        # Deepcopy to avoid the dictionaries being passed by reference
        # so we can check against the original object later
        mock_get_stats.return_value = copy.deepcopy(sample_stats)
        stats = self.mysqs.get_stats()
        # aliased field is changed to unaliased form
        assert "year_i" not in stats["stats_fields"]
        assert "year" in stats["stats_fields"]
        # value of field is preserved without chang
        assert stats["stats_fields"]["year"] == sample_stats["stats_fields"]["year_i"]
        # unaliased field is left alone
        assert "start_i" in stats["stats_fields"]
        assert (
            stats["stats_fields"]["start_i"] == sample_stats["stats_fields"]["start_i"]
        )
        # ensure that if get_stats returns None on error,
        # we don't have a key error when try to realias fields
        mock_get_stats.return_value = None
        assert self.mysqs.get_stats() is None

    @patch("parasolr.query.queryset.SolrQuerySet.get_highlighting")
    def test_get_highlighting(self, mock_get_highlighting):
        sample_highlights = {
            # In setup for tests, name_t is aliased to name
            "item.1": {
                "name_t": ["snippet 1", "snippet 2"],
                "description_t": ["another snippet"],
            }
        }
        # Deepcopy to avoid the dictionaries being passed by reference
        # so we can check against the original object later
        mock_get_highlighting.return_value = copy.deepcopy(sample_highlights)
        highlights = self.mysqs.get_highlighting()
        # aliased field is changed to unaliased form
        assert "name_t" not in highlights["item.1"]
        assert "name" in highlights["item.1"]
        # value of field is preserved without change
        assert highlights["item.1"]["name"] == sample_highlights["item.1"]["name_t"]
        # unaliased field is left alone
        assert "description_t" in highlights["item.1"]

        # ensure that if get_stats returns None on error,
        # we don't have a key error when try to realias fields
        mock_get_highlighting.return_value = None
        assert self.mysqs.get_highlighting() is None
