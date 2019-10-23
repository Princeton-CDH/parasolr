from parasolr.indexing import Indexable

try:
    from django.db.models.fields.related_descriptors import ManyToManyDescriptor
    django = True
except ImportError:
    django = None

if django:

    class ModelIndexable(Indexable):

        # these start out as None until they're calculated when identifying
        # dependencies below
        related = None
        m2m = None

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
            for model in cls.__subclasses__():
                # if no dependencies specified, skip
                if not hasattr(model, 'index_depends_on'):
                    continue
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

        # Prevent ModelIndexable from itself being indexed - only subclasses
        # should be considered for `Indexable.all_indexables`
        class Meta:
            abstract = True