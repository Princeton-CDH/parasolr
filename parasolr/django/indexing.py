import logging

from parasolr.indexing import Indexable

try:
    from django.apps import apps
    from django.db.models.fields import related_descriptors
    django = True
except ImportError:
    django = None


logger = logging.getLogger(__name__)

if django:

    class ModelIndexable(Indexable):

        # Prevent ModelIndexable from itself being indexed - only subclasses
        # should be included in  `Indexable.all_indexables`
        class Meta:
            abstract = True

        # these start out empty; calculated when identifying
        # dependencies below
        related = {}
        m2m = []
        separator = '__'

        @staticmethod
        def get_related_model(model, name):

            # support app.Model notation
            if '.' in name:
                app, model_name = name.split('.')
                return apps.get_app_config(app).get_model(model_name)

            related_model = None

            # if __ in str, split and recurse
            if ModelIndexable.separator in name:
                current, rest = name.split(ModelIndexable.separator, 1)
                related_model = ModelIndexable.get_related_model(model,
                                                                 current)
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

            elif isinstance(attr,
                            related_descriptors.ReverseManyToOneDescriptor):
                related_model = attr.rel.related_model

            if related_model:
                return related_model
            else:
                logger.warning('Unhandled related model: %s on %r' %
                               (name, model))

        @classmethod
        def identify_index_dependencies(cls):
            '''Identify and set lists of index dependencies for the subclass
            of :class:`Indexable`.
            '''
            # determine and document index dependencies
            # for indexable models based on index_depends_on field

            # if index dependencies have already been gathered, do nothing
            if cls.related or cls.m2m:
                return

            related = {}
            m2m = []
            for model in cls.__subclasses__():
                # if no dependencies specified, skip
                if not hasattr(model, 'index_depends_on'):
                    continue
                for dep, opts in model.index_depends_on.items():
                    # get related model
                    related_model = cls.get_related_model(model, dep)
                    related[related_model] = opts

                    # check for through model
                    if hasattr(model, dep):
                        attr = getattr(model, dep)
                        if isinstance(
                           attr, related_descriptors.ManyToManyDescriptor):
                            # add through model to many to many list
                            m2m.append(attr.through)

            cls.related = related
            cls.m2m = m2m
