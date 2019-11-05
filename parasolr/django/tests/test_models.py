"""
Test models for testing index dependency logic and signals.

"""

try:
    from django.db import models

    from parasolr.django.indexing import ModelIndexable
except ImportError:
    pass


# an empty model that can have many TestItem as members
class Collection(models.Model):
    class Meta:
        app_label = 'parasolr'


def signal_method(*args, **kwargs):
    pass


# an indexable django model that has dependencies
class IndexItem(models.Model, ModelIndexable):
    collections = models.ManyToManyField(Collection)

    index_depends_on = {
        'collections': {
            'save': signal_method,
            'delete': signal_method
        }
    }

    class Meta:
        app_label = 'parasolr'


# model with a reverse many to many to the indexable item
class Owner(models.Model):
    items = models.ManyToManyField(IndexItem)
    collections = models.ManyToManyField(Collection)

    class Meta:
        app_label = 'parasolr'


# item with no index_depends_on declared should not cause an error
class IndependentItem(models.Model, ModelIndexable):
    class Meta:
        abstract = True
