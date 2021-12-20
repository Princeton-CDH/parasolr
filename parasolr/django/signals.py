"""

This module provides on-demand reindexing of Django models when they
change, based on Django signals. To use this signal handler, import
import it in the `ready` method of a django app. This will
automatically bind connect any configured signal handlers::

    from django.apps import AppConfig

    class MyAppConfig(AppConfig):
        name = 'myapp'

        def ready(self):
            # import and connect signal handlers for Solr indexing
            from parasolr.django.signals import IndexableSignalHandler

To configure index dependencies, add a property on any
:class:`~parasolr.django.indexing.ModelIndexable` subclass with the
dependencies and signals that should trigger reindexing.  Example::

    class MyModel(ModelIndexable):

        index_depends_on = {
            'collections': {
                'post_save': signal_method,
                'pre_delete': signal_method
            }
        }


The keys of the dependency dict can be:

- an attribute on the indexable model (i.e., the name of a many-to-many
  relationship); this will bind an additional signal handler on the m2m
  relationship change.
- an attribute on a related model using django queryset notation (use this
  for a secondary many-to many relationship, e.g. `collections__authors`)
- a string with the model name in app.ModelName notation, to find and
  load a model directly

The dictionaries for each related model or attribute should contain:

- a key with the :mod:`django.db.models.signals` signal to bind
- a signal handler to bind

Currently attribute lookup only supports many-to-many and reverse
many-to-many relationships.

Typically you will want to bind post_save and pre_delete for many-to-many
relationships.

"""


import logging

try:
    from django.db import models

    django = True
except ImportError:
    django = None

from parasolr.django.indexing import ModelIndexable
from parasolr.django.util import requires_django

logger = logging.getLogger(__name__)


@requires_django
class IndexableSignalHandler:
    """Signal handler for indexing Django model-based indexables.
    Automatically identifies and binds handlers based on configured
    index dependencies on indexable objects..
    """

    @staticmethod
    def handle_save(sender, instance, **kwargs):
        """reindex on save if an instance of
        :class:`~parasolr.django.indexing.ModelIndexable`"""
        if isinstance(instance, ModelIndexable):
            logger.debug("Indexing %r", instance)
            instance.index()

    @staticmethod
    def handle_delete(sender, instance, **kwargs):
        """remove from index on delete if an instance of
        :class:`~parasolr.django.indexing.ModelIndexable`"""
        logger.debug("Deleting %r from index", instance)
        if isinstance(instance, ModelIndexable):
            instance.remove_from_index()

    @staticmethod
    def handle_relation_change(sender, instance, action, **kwargs):
        """index on add, remove, and clear for
        :class:`~parasolr.django.indexing.ModelIndexable` instances"""
        if action in ["post_add", "post_remove", "post_clear"]:
            if isinstance(instance, ModelIndexable):
                logger.debug("Indexing %r (m2m change: %s)", instance, action)
                instance.index()

    @staticmethod
    def connect():
        """bind indexing signal handlers to save and delete signals for
        :class:`~ppa.archive.solr.Indexable` subclassess and any
        indexing dependencies"""

        # bind to save and delete signals for ModelIndexable subclasses
        for model in ModelIndexable.__subclasses__():
            logger.debug("Registering signal handlers for %s", model)
            models.signals.post_save.connect(
                IndexableSignalHandler.handle_save, sender=model
            )
            models.signals.post_delete.connect(
                IndexableSignalHandler.handle_delete, sender=model
            )

        ModelIndexable.identify_index_dependencies()
        for m2m_rel in ModelIndexable.m2m:
            logger.debug("Registering m2m signal handler for %s", m2m_rel)
            models.signals.m2m_changed.connect(
                IndexableSignalHandler.handle_relation_change, sender=m2m_rel
            )

        for model, options in ModelIndexable.related:
            for signal_name, handler in options.items():
                model_signal = getattr(models.signals, signal_name)
                logger.debug(
                    "Registering %s signal handler %s for %s",
                    handler,
                    signal_name,
                    model,
                )
                model_signal.connect(handler, sender=model)

    @staticmethod
    def disconnect():
        """disconnect indexing signal handlers"""
        for model in ModelIndexable.__subclasses__():
            logger.debug("Disconnecting signal handlers for %s", model)
            models.signals.post_save.disconnect(
                IndexableSignalHandler.handle_save, sender=model
            )
            models.signals.post_delete.disconnect(
                IndexableSignalHandler.handle_delete, sender=model
            )

        for m2m_rel in ModelIndexable.m2m:
            logger.debug("Disconnecting m2m signal handler for %s", m2m_rel)
            models.signals.m2m_changed.disconnect(
                IndexableSignalHandler.handle_relation_change, sender=m2m_rel
            )

        for model, options in ModelIndexable.related:
            for signal_name, handler in options.items():
                model_signal = getattr(models.signals, signal_name)
                logger.debug(
                    "Disconnecting %s signal handler for %s", signal_name, model
                )
                model_signal.disconnect(handler, sender=model)


if django:
    IndexableSignalHandler.connect()
