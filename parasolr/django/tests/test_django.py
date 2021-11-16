import logging
from unittest.mock import Mock, patch

import pytest

try:
    import django
    from django.core.exceptions import ImproperlyConfigured
    from django.db.models import Manager
    from django.test import override_settings

    from parasolr.django import AliasedSolrQuerySet, SolrClient, SolrQuerySet
    from parasolr.django.indexing import ModelIndexable
    from parasolr.django.tests.test_models import (
        Collection,
        IndexItem,
        NothingToIndex,
        Owner,
    )
    from parasolr.indexing import Indexable

except ImportError:
    django = None

from parasolr.tests.utils import skipif_django, skipif_no_django


@skipif_no_django
def test_django_solrclient():

    # check error handling

    # no config
    with override_settings(SOLR_CONNECTIONS=None):
        with pytest.raises(ImproperlyConfigured) as excinfo:
            SolrClient()
        assert "requires SOLR_CONNECTIONS in settings" in str(excinfo.value)

    # config but no default
    with override_settings(SOLR_CONNECTIONS={"foo": "bar"}):
        with pytest.raises(ImproperlyConfigured) as excinfo:
            SolrClient()
        assert 'No "default" section in SOLR_CONNECTIONS configuration' in str(
            excinfo.value
        )

    # default config but no URL
    with override_settings(SOLR_CONNECTIONS={"default": {"foo": "bar"}}):
        with pytest.raises(ImproperlyConfigured) as excinfo:
            SolrClient()
        assert "No URL in default SOLR_CONNECTIONS configuration" in str(excinfo.value)

    # url but no collection
    config = {"URL": "http://my.solr.com:8943/solr"}
    with override_settings(SOLR_CONNECTIONS={"default": config}):
        solr = SolrClient()
        assert solr.solr_url == config["URL"]
        assert solr.collection == ""

    # url and collection
    config["COLLECTION"] = "mycore"
    with override_settings(SOLR_CONNECTIONS={"default": config}):
        solr = SolrClient()
        assert solr.solr_url == config["URL"]
        assert solr.collection == config["COLLECTION"]

    # commit within option
    config["COMMITWITHIN"] = 750
    with override_settings(SOLR_CONNECTIONS={"default": config}):
        solr = SolrClient()
        assert solr.commitWithin == 750

        # but passed in value takes precedence
        solr = SolrClient(commitWithin=7339)
        assert solr.commitWithin == 7339


@skipif_django
def test_no_django_solrclient():
    # should not be defined when django is not installed
    with pytest.raises(ImportError):
        from parasolr.django import SolrClient


@skipif_django
def test_no_django_solr_solrclient():
    # should not be defined when django is not installed
    with pytest.raises(ImportError):
        from parasolr.solr.django.solr import SolrClient


@skipif_django
def test_no_django_queryset():
    # should not be defined when django is not installed
    with pytest.raises(ImportError):
        from parasolr.django.queryset import SolrQuerySet


@skipif_django
def test_no_django_modelindexable():
    # should not be defined when django is not installed
    with pytest.raises(ImportError):
        from parasolr.django.indexing import ModelIndexable


@skipif_no_django
@patch("parasolr.django.queryset.SolrClient")
def test_django_solrqueryset(mocksolrclient):
    # auto-initialize solr connection if not specified
    sqs = SolrQuerySet()
    mocksolrclient.assert_called_with()
    assert sqs.solr == mocksolrclient.return_value
    mocksolrclient.reset_mock()

    # use solr client if passed in
    mymocksolr = Mock(spec=SolrClient)
    sqs = SolrQuerySet(solr=mymocksolr)
    assert sqs.solr == mymocksolr
    mocksolrclient.assert_not_called()


@skipif_no_django
@patch("parasolr.django.queryset.SolrClient")
def test_django_aliasedsolrqueryset(mocksolrclient):
    class MyAliasedSolrQuerySet(AliasedSolrQuerySet):
        """extended version of AliasedSolrQuerySet for testing"""

        #: map app/readable field names to actual solr fields
        field_aliases = {
            "name": "name_t",
            "year": "year_i",
            "has_info": "has_info_b",
        }

    # django queryset behavior: auto-initialize solr connection if not specified
    mysqs = MyAliasedSolrQuerySet()
    mocksolrclient.assert_called_with()
    assert mysqs.solr == mocksolrclient.return_value
    mocksolrclient.reset_mock()

    # alias queryset init: field list and reverse alias lookup populated
    assert mysqs.field_list
    assert mysqs.reverse_aliases


@skipif_no_django
@patch("parasolr.django.queryset.SolrClient")
def test_identify_index_dependencies(mocksolrclient):

    ModelIndexable.identify_index_dependencies()

    # collection model should be in related object config
    # convert list of tuples back into dict for testing
    related_models = {model: opts for model, opts in ModelIndexable.related}
    assert Collection in related_models
    # assert Collection in ModelIndexable.related
    # save/delete handler config options saved
    assert related_models[Collection] == IndexItem.index_depends_on["collections"]
    # through model added to m2m list
    assert IndexItem.collections.through in ModelIndexable.m2m

    # dependencies should be cached on the first run and not regenerated
    with patch.object(ModelIndexable, "__subclasses__") as mockgetsubs:
        ModelIndexable.identify_index_dependencies()
        assert mockgetsubs.call_count == 0


@skipif_no_django
def test_get_related_model(caplog):
    # test app.Model notation with stock django model
    from django.contrib.auth.models import User

    assert ModelIndexable.get_related_model(IndexItem, "auth.User") == User

    # many to many
    assert ModelIndexable.get_related_model(IndexItem, "collections") == Collection

    # reverse many to many
    assert ModelIndexable.get_related_model(IndexItem, "owner_set") == Owner

    # multipart path
    assert (
        ModelIndexable.get_related_model(IndexItem, "owner_set__collections")
        == Collection
    )

    # foreign key is now supported!
    assert ModelIndexable.get_related_model(IndexItem, "primary") == Collection

    # use mock to test taggable manager behavior
    mockitem = Mock()
    mockitem.tags = Mock(spec=Manager, through=Mock())
    mockitem.tags.through.tag_model.return_value = "TagBase"
    assert ModelIndexable.get_related_model(mockitem, "tags") == "TagBase"

    # if relation cannot be determined, should warn
    with caplog.at_level(logging.WARNING):
        assert not ModelIndexable.get_related_model(mockitem, "foo")
        assert "Unhandled related model" in caplog.text


# these classes cannot be defined without django dependencies
if django:

    @skipif_no_django
    class TestModelIndexable:
        class NoMetaModelIndexable(NothingToIndex, ModelIndexable):
            """indexable subclass that should be indexed"""

        class AbstractModelIndexable(ModelIndexable):
            """abstract indexable subclass that should NOT be indexed"""

            class Meta:
                abstract = True

        class NonAbstractModelIndexable(NothingToIndex, ModelIndexable):
            """indexable subclass that should be indexed"""

            class Meta:
                abstract = False

        def test_all_indexables(self):
            indexables = Indexable.all_indexables()

            assert ModelIndexable not in indexables
            assert self.NoMetaModelIndexable in indexables
            assert self.AbstractModelIndexable not in indexables
            assert self.NonAbstractModelIndexable in indexables
