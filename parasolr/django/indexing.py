"""

This module provides indexing support for Django models.  Also see
:class:`~parasolr.indexing.Indexable`.

To use, add :class:`ModelIndexable` as a mixin to the model class
you want to be indexed.  At minimum, you'll want to extend the
`index_data` method to include the data you want in the indexed::

    def index_data(self):
        index_data = super().index_data()

        # if there are some records that should not be included
        # return id only. This will blank out any previously indexed
        # values, and item will not be findable by type.
        # if not ...
            # del index_data['item_type']
            # return index_data

        # add values to index data
        index_data.update({
            ...
        })
        return index_data

You can optionally extend :meth:`~parasolr.indexing.Indexable.items_to_index`
and :meth:`~parasolr.indexing.Indexable.index_item_type`.

-------------------------

"""

import logging

from parasolr.django.util import requires_django
from parasolr.indexing import Indexable

try:
    from django.apps import apps
    from django.db.models import Manager, Model
    from django.db.models.fields import related_descriptors
except ImportError:
    # define placeholder model class so ModelIndexable can be defined
    class Model:
        pass


logger = logging.getLogger(__name__)


@requires_django
class ModelIndexable(Model, Indexable):
    # Prevent ModelIndexable from itself being indexed - only subclasses
    # should be included in  `Indexable.all_indexables`
    class Meta:
        abstract = True

    # these start out empty; calculated when identifying
    # dependencies below
    related = {}
    m2m = []
    separator = "__"

    @staticmethod
    def get_related_model(model, name):
        """Find a related model for use in signal-based indexing. Supports
        app.Model notation or attribute on the current model (supports
        queryset syntax for attributes on related models.)
        """

        # support app.Model notation
        if "." in name:
            app, model_name = name.split(".")
            return apps.get_app_config(app).get_model(model_name)

        related_model = None

        # if __ in str, split and recurse
        if ModelIndexable.separator in name:
            current, rest = name.split(ModelIndexable.separator, 1)
            related_model = ModelIndexable.get_related_model(model, current)
            return ModelIndexable.get_related_model(related_model, rest)

        attr = getattr(model, name)

        if isinstance(attr, related_descriptors.ManyToManyDescriptor):
            # store related model and options
            # get related model from the many-to-many relation
            related_model = attr.rel.model
            # if rel.model is *this* model (i.e., this is a
            # reverse many to many), get the other model
            if attr.rel.model == model:
                related_model = attr.rel.related_model

        elif isinstance(attr, related_descriptors.ReverseManyToOneDescriptor):
            related_model = attr.rel.related_model

        elif isinstance(attr, related_descriptors.ForwardManyToOneDescriptor):
            # many to one, i.e. foreign key
            related_model = attr.field.related_model

        elif isinstance(attr, Manager):
            # specific to django-taggit TaggableManager
            if hasattr(attr.through, "tag_model"):
                related_model = attr.through.tag_model()

        if related_model:
            return related_model

        logger.warning("Unhandled related model: %s on %r" % (name, model))

    @classmethod
    def identify_index_dependencies(cls):
        """Identify and set lists of index dependencies for the subclass
        of :class:`Indexable`.
        """
        # determine and document index dependencies
        # for indexable models based on index_depends_on field

        # if index dependencies have already been gathered, do nothing
        if cls.related or cls.m2m:
            return

        related = []
        m2m = []
        for model in cls.__subclasses__():
            # if no dependencies specified, skip
            if not hasattr(model, "index_depends_on"):
                continue
            for dep, opts in model.index_depends_on.items():
                # get related model
                related_model = cls.get_related_model(model, dep)
                related.append((related_model, opts))

                # check for through model
                if hasattr(model, dep):
                    attr = getattr(model, dep)
                    if isinstance(
                        attr, (Manager, related_descriptors.ManyToManyDescriptor)
                    ):
                        # add through model to many to many list
                        m2m.append(attr.through)

        cls.related = related
        cls.m2m = m2m
