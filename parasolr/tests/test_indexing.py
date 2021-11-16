from unittest.mock import MagicMock, Mock, patch

import pytest

try:
    from django.db.models.query import QuerySet
except ImportError:
    QuerySet = None

from parasolr.indexing import Indexable
from parasolr.tests.utils import skipif_no_django

# Define Indexable subclasses for testing
# Used for both Indexable and index manage command


class SimpleIndexable(Indexable):
    """simple indexable subclass"""

    id = "a"

    @classmethod
    def index_item_type(cls):
        return "simple"

    # nededed for index manage command (assumes django model)
    class objects:
        def count():
            return 5

        def all():
            return [SimpleIndexable() for i in range(5)]


class MockModelIndexable(Indexable):
    """mock-model indexable subclass"""

    id = 1

    class _meta:
        verbose_name = "model"

    # nededed for index manage command
    class objects:
        def count():
            return 1

        def all():
            return [MockModelIndexable()]


class AbstractIndexable(Indexable):
    """indexable subclass that should not (itself) be indexed"""

    class _meta:
        abstract = True


class SubIndexable(SimpleIndexable):
    """indexable sub-subclass that should be included in all_indexables"""

    pass


class SubAbstractIndexable(SimpleIndexable):
    class _meta:
        abstract = True


@skipif_no_django
@patch.object(Indexable, "solr")
class TestIndexable:
    def test_all_indexables(self, mocksolr):
        indexables = Indexable.all_indexables()
        assert SimpleIndexable in indexables
        assert MockModelIndexable in indexables
        assert AbstractIndexable not in indexables
        assert SubIndexable in indexables
        assert SubAbstractIndexable not in indexables

    def test_index_item_type(self, mocksolr):
        # use model verbose name by default
        assert MockModelIndexable().index_item_type() == "model"

    def test_index_id(self, mocksolr):
        assert SimpleIndexable().index_id() == "simple.a"
        assert MockModelIndexable().index_id() == "model.1"

    def test_index_data(self, mocksolr):
        model = MockModelIndexable()
        data = model.index_data()
        assert data["id"] == model.index_id()
        assert data["item_type_s"] == model.index_item_type()
        assert len(data) == 2

    def test_index(self, mocksolr):
        # index method on a single object instance
        model = MockModelIndexable()
        model.index()
        # NOTE: because solr is stored on the class,
        # mocksolr.return_value is not the same object
        model.solr.update.index.assert_called_with([model.index_data()])

    def test_remove_from_index(self, mocksolr):
        # remove from index method on a single object instance
        model = MockModelIndexable()
        model.remove_from_index()
        model.solr.update.delete_by_id.assert_called_with([model.index_id()])

    def test_index_items(self, mocksolr):
        items = [SimpleIndexable() for i in range(10)]

        indexed = Indexable.index_items(items)
        assert indexed == len(items)
        Indexable.solr.update.index.assert_called_with([i.index_data() for i in items])

        # index in chunks
        Indexable.index_chunk_size = 6
        Indexable.solr.reset_mock()
        indexed = Indexable.index_items(items)
        assert indexed == len(items)
        # first chunk
        Indexable.solr.update.index.assert_any_call([i.index_data() for i in items[:6]])
        # second chunk
        Indexable.solr.update.index.assert_any_call([i.index_data() for i in items[6:]])

        # pass in a progressbar object
        mock_progbar = Mock()
        Indexable.index_items(items, progbar=mock_progbar)
        # progress bar update method should be called once for each chunk
        assert mock_progbar.update.call_count == 2

    def test_index_items__queryset(self, mocksolr):
        # index a queryset
        mockqueryset = MagicMock(spec=QuerySet)
        Indexable.index_items(mockqueryset)
        mockqueryset.iterator.assert_called_with()

    def test_items_to_index(self, mocksolr):
        # assumes django model manager interface by default

        # simple object with objects.all interface
        simple_items_to_index = SimpleIndexable.items_to_index()
        assert len(simple_items_to_index) == 5
        assert isinstance(simple_items_to_index[0], SimpleIndexable)

        # model-ish object
        model_items_to_index = MockModelIndexable.items_to_index()
        assert len(model_items_to_index) == 1
        assert isinstance(model_items_to_index[0], MockModelIndexable)

        class NonModelIndexable(Indexable):
            pass

        # raises not implemented if objects.all fails
        with pytest.raises(NotImplementedError):
            NonModelIndexable.items_to_index()

    def test_total_to_index(self, mocksolr):
        # assumes django model manager interface by default

        # simple object with objects.all interface
        assert SimpleIndexable.total_to_index() == 5

        # model-ish object
        assert MockModelIndexable.total_to_index() == 1

        class NonModelIndexable(Indexable):
            pass

        # raises not implemented if objects.all fails
        with pytest.raises(NotImplementedError):
            NonModelIndexable.total_to_index()
