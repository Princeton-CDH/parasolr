from parasolr.indexing import Indexable

try:
    from django.db.models.fields.related_descriptors import ManyToManyDescriptor
    django = True
except ImportError:
    django = None

if django:

    class ModelIndexable(Indexable):

        @classmethod
        def identify_index_dependencies(cls):
            '''Identify and set lists of index dependencies for the subclass
            of :class:`Indexable`.
            '''
            # determine and document index dependencies
            # for indexable models based on index_depends_on field

            if cls.related is not None and cls.m2m is not None:
                return

            related = {}
            m2m = []
            for model in Indexable.__subclasses__():
                for dep, opts in model.index_depends_on.items():
                    # if a string, assume attribute of model
                    if isinstance(dep, str):
                        attr = getattr(model, dep)
                        if isinstance(attr, ManyToManyDescriptor):
                            # store related model and options with signal handlers
                            related[attr.rel.model] = opts
                            # add through model to many to many list
                            m2m.append(attr.through)

            cls.related = related
            cls.m2m = m2m