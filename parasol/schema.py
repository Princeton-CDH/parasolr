'''
Solr schema configuration and management


'''
import logging


logger = logging.getLogger(__name__)


class SolrField:
    """A descriptor for declaring a solr field on a :class:`SolrSchema`
    instance.
    """

    def __init__(self, fieldtype, required=False, multivalued=False):
        self.type = fieldtype
        self.required = required
        self.multivalued = multivalued

    def __get__(self, obj, objtype):
        return {'type': self.type, 'required': self.required,
                'multiValued': self.multivalued}

    def __set__(self, obj, val):
        # read-only descriptor
        raise AttributeError


class SolrTypedField(SolrField):
    '''Base class for typed solr field descriptor. For use with your own
    field types, extend and set :attr:`field_type`.'''
    field_type = None

    def __init__(self, *args, **kwargs):
        super().__init__(self.field_type, *args, **kwargs)


class SolrStringField(SolrTypedField):
    '''Solr string field'''
    field_type = 'string'


class SolrSchema:
    '''Solr schema configuration'''

    @classmethod
    def get_configuration(cls):
        '''Find a SolrSchema subclass for use as schema configuration.
        Currently only supports one schema configuration.'''
        subclasses = cls.__subclasses__()
        if not subclasses:
            raise Exception('No Solr schema configuration found')
        elif len(subclasses) > 1:
            raise Exception('Currently only one Solr schema configuration is supported (found %d)' \
                             % len(subclasses))

        return subclasses[0]

    @classmethod
    def get_field_names(cls):
        '''iterate over class attributes and return all that are instances of
        :class:`SolrField`'''
        return [attr_name for attr_name, attr_type in cls.__dict__.items()
                if isinstance(attr_type, SolrField)]

    @classmethod
    def update_solr_fields(cls, solr):
        '''Update the configured Solr instance schema to match
        the configured fields.  Returns a tuple with the number of fields
        created and updated.'''

        current_fields = [field.name for field in solr.schema.list_fields()]
        configured_field_names = cls.get_field_names()

        created = updated = removed = 0
        for field_name in configured_field_names:
            field_opts = getattr(cls, field_name)
            if field_name not in current_fields:
                logger.debug('Adding schema field %s %s', field_name, field_opts)
                solr.schema.add_field(name=field_name, **field_opts)
                created += 1
            else:
                logger.debug('Replace schema field %s %s', field_name, field_opts)
                solr.schema.replace_field(name=field_name, **field_opts)
                updated += 1

        # remove previously defined fields that are no longer current
        for field_name in current_fields:
            # don't remove special fields!
            if field_name == 'id' or field_name.startswith('_'):
                continue
            if field_name not in configured_field_names:
                removed += 1
                logger.debug('Delete schema field %s', field_name)
                solr.schema.delete_field(field_name)

        return (created, updated, removed)
