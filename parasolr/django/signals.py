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

    class MyModel(Model, ModelIndexable):

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

logger = logging.getLogger(__name__)


if django:

    class IndexableSignalHandler:

        @staticmethod
        def handle_save(sender, instance, **kwargs):
            if isinstance(instance, ModelIndexable):
                logger.debug('Indexing %r', instance)
                instance.index()

        @staticmethod
        def handle_delete(sender, instance, **kwargs):
            logger.debug('Deleting %r from index', instance)
            if isinstance(instance, ModelIndexable):
                instance.remove_from_index()

        @staticmethod
        def handle_relation_change(sender, instance, action, **kwargs):
            # handle add, remove, and clear for ModelIndexable instances
            if action in ['post_add', 'post_remove', 'post_clear']:
                if isinstance(instance, ModelIndexable):
                    logger.debug('Indexing %r (m2m change)', instance)
                    instance.index()

        @staticmethod
        def connect():
            '''bind indexing signal handlers to save and delete signals for
            :class:`~ppa.archive.solr.Indexable` subclassess and any
            indexing dependencies'''

            # bind to save and delete signals for ModelIndexable subclasses
            for model in ModelIndexable.__subclasses__():
                logger.debug('Registering signal handlers for %s', model)
                models.signals.post_save.connect(
                    IndexableSignalHandler.handle_save, sender=model)
                models.signals.post_delete.connect(
                    IndexableSignalHandler.handle_delete, sender=model)

            ModelIndexable.identify_index_dependencies()
            for m2m_rel in ModelIndexable.m2m:
                logger.debug('Registering m2m signal handler for %s', m2m_rel)
                models.signals.m2m_changed.connect(
                    IndexableSignalHandler.handle_relation_change,
                    sender=m2m_rel)

            for model, options in ModelIndexable.related.items():
                for signal_name, handler in options.items():
                    model_signal = getattr(models.signals, signal_name)
                    logger.debug('Registering %s signal handler for %s',
                                 signal_name, model)
                    model_signal.connect(handler, sender=model)

        @staticmethod
        def disconnect():
            '''disconnect indexing signal handlers'''
            for model in ModelIndexable.__subclasses__():
                logger.debug('Disconnecting signal handlers for %s', model)
                models.signals.post_save.disconnect(
                    IndexableSignalHandler.handle_save, sender=model)
                models.signals.post_delete.disconnect(
                    IndexableSignalHandler.handle_delete, sender=model)

            for m2m_rel in ModelIndexable.m2m:
                logger.debug('Disconnecting m2m signal handler for %s',
                             m2m_rel)
                models.signals.m2m_changed.disconnect(
                    IndexableSignalHandler.handle_relation_change,
                    sender=m2m_rel)

            for model, options in ModelIndexable.related.items():
                if 'save' in options:
                    logger.debug('Disconnecting save signal handler for %s',
                                 model)
                    models.signals.pre_save.disconnect(options['save'],
                                                       sender=model)
                if 'delete' in options:
                    logger.debug('Disconnecting delete signal handler for %s',
                                 model)
                    models.signals.pre_delete.disconnect(
                        options['delete'], sender=model)

    IndexableSignalHandler.connect()
