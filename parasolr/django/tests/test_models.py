"""
Test models for testing index dependency logic and signals.

"""

try:
    import django
    from django.db import models

    from parasolr.django.indexing import ModelIndexable
except ImportError:
    django = None


class NothingToIndex:
    # mixin with class methods required to avoid test on
    # index command trying to query django db and index
    @classmethod
    def items_to_index(cls):
        return []

    @classmethod
    def total_to_index(cls):
        return 0


if django:

    def signal_method(*args, **kwargs):
        pass

    # an empty model that can have many TestItem as members
    class Collection(models.Model):
        class Meta:
            app_label = "parasolr"

    # an indexable django model that has dependencies
    class IndexItem(NothingToIndex, ModelIndexable):
        collections = models.ManyToManyField(Collection)
        primary = models.ForeignKey(Collection, on_delete=models.SET_NULL)

        index_depends_on = {
            "collections": {"post_save": signal_method, "pre_delete": signal_method}
        }

        class Meta:
            app_label = "parasolr"

    # model with a reverse many to many to the indexable item
    class Owner(models.Model):
        item = models.ForeignKey(IndexItem, on_delete=models.SET_NULL)
        collections = models.ManyToManyField(Collection)

        class Meta:
            app_label = "parasolr"

    # item with no index_depends_on declared should not cause an error
    class IndependentItem(ModelIndexable):
        class Meta:
            abstract = True

    # something is overriding this (inheritance?); ensure set as abstract
    IndependentItem.Meta.abstract = True
