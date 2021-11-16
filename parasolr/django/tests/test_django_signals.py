from unittest.mock import Mock, patch
from weakref import ref

import pytest

try:
    from django.db import models

    # from parasolr.django.indexing import ModelIndexable
    from parasolr.django.signals import IndexableSignalHandler
    from parasolr.django.tests import test_models
except ImportError:
    IndexableSignalHandler = None

from parasolr.tests.utils import skipif_django, skipif_no_django


def setup_module():
    # connect indexing signal handlers for this test module only
    if IndexableSignalHandler:
        IndexableSignalHandler.connect()


def teardown_module():
    # disconnect indexing signal handlers
    if IndexableSignalHandler:
        IndexableSignalHandler.disconnect()


@skipif_django
def test_no_django_indexable():
    # should not be defined when django is not installed
    with pytest.raises(ImportError):
        from parasolr.django.signals import IndexableSignalHandler


@skipif_no_django
class TestIndexableSignalHandler:
    def test_connect(self):
        # check that signal handlers are connected as expected
        # - model save and delete
        post_save_handlers = [item[1] for item in models.signals.post_save.receivers]
        assert ref(IndexableSignalHandler.handle_save) in post_save_handlers
        post_del_handlers = [item[1] for item in models.signals.post_delete.receivers]
        assert ref(IndexableSignalHandler.handle_delete) in post_del_handlers
        # many to many
        m2m_handlers = [item[1] for item in models.signals.m2m_changed.receivers]
        assert ref(IndexableSignalHandler.handle_relation_change) in m2m_handlers

        # testing related handlers based on test models
        post_save_handlers = [item[1] for item in models.signals.post_save.receivers]
        assert ref(test_models.signal_method) in post_save_handlers
        pre_del_handlers = [item[1] for item in models.signals.pre_delete.receivers]
        assert ref(test_models.signal_method) in pre_del_handlers

    def test_handle_save(self):
        instance = test_models.IndexItem()
        with patch.object(instance, "index") as mockindex:
            # call directly
            IndexableSignalHandler.handle_save(Mock(), instance)
            mockindex.assert_any_call()

            # call via signal
            mockindex.reset_mock()
            models.signals.post_save.send(test_models.IndexItem, instance=instance)
            mockindex.assert_any_call()

        # non-indexable object should be ignored
        nonindexable = Mock()
        IndexableSignalHandler.handle_save(Mock(), nonindexable)
        nonindexable.index.assert_not_called()

    def test_handle_delete(self):
        with patch.object(test_models.IndexItem, "remove_from_index") as mock_rmindex:
            instance = test_models.IndexItem()
            IndexableSignalHandler.handle_delete(Mock(), instance)
            mock_rmindex.assert_called_with()

        # non-indexable object should be ignored
        nonindexable = Mock()
        IndexableSignalHandler.handle_delete(Mock(), nonindexable)
        nonindexable.remove_from_index.assert_not_called()

    @pytest.mark.django_db
    def test_handle_relation_change(self):
        instance = test_models.IndexItem()
        with patch.object(instance, "index") as mockindex:
            # call directly - supported actions
            for action in ["post_add", "post_remove", "post_clear"]:

                mockindex.reset_mock()
                IndexableSignalHandler.handle_relation_change(
                    test_models.IndexItem, instance, action
                )
                mockindex.assert_any_call()

            # if action is not one we care about, should be ignored
            mockindex.reset_mock()
            IndexableSignalHandler.handle_relation_change(
                test_models.IndexItem, instance, "pre_remove"
            )
            mockindex.assert_not_called()

        # non-indexable object should be ignored
        nonindexable = Mock()
        IndexableSignalHandler.handle_relation_change(Mock(), nonindexable, "post_add")
        nonindexable.index.assert_not_called()
