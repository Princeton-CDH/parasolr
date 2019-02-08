"""
Solr schema configuration and management


"""
import logging

from attrdict import AttrDefault


logger = logging.getLogger(__name__)


class SolrField:
    """A descriptor for declaring a solr field on a :class:`SolrSchema`
    instance.
    """

    def __init__(self, fieldtype, required=False, multivalued=False):
        """
        :param fieldtype: The type of Solr field.
        :type fieldtype: str
        :param required: Whether the field is required.
        :type required: bool
        :param multivalued: Whether the field is multi-valued.
        :type multivalued: bool
        """
        self.type = fieldtype
        self.required = required
        self.multivalued = multivalued

    def __get__(self, obj, objtype):
        return {'type': self.type, 'required': self.required,
                'multiValued': self.multivalued}

    def __set__(self, obj, val):
        # enforce read-only descriptor
        raise AttributeError


class SolrTypedField(SolrField):
    """Base class for typed solr field descriptor. For use with your own
    field types, extend and set :attr:`field_type`."""
    field_type = None

    def __init__(self, *args, **kwargs):
        super().__init__(self.field_type, *args, **kwargs)


class SolrStringField(SolrTypedField):
    """Solr string field."""
    field_type = 'string'


class SolrAnalyzer:
    """Class to declare a solr field analyzer with tokenizer and filters,
    for use with :class:`SolrFieldType`."""

    #: string name of the tokenizer to use
    tokenizer = None
    #: list of the filters to apply
    filters = None

    @classmethod
    def as_solr_config(cls):
        """Return analyzer information for use in solr configuration."""
        return {
            'tokenizer': {
                'class': cls.tokenizer
            },
            'filters': cls.filters
        }


class SolrFieldType:
    """A descriptor for declaring and configure a solr field type on
    a :class:`SolrSchema`instance.
    """
    def __init__(self, field_class, analyzer):
        """
        :param field_class: The class of the Solr field
        :type field_class: str
        :param analyzer: The name of the Solr analyzer to use on the field.
        :type analyzer: str
        """
        self.field_class = field_class
        self.analyzer = analyzer

    def __get__(self, obj, objtype):
        # return format neded for declaring field type
        return {
            'class': self.field_class,
            'analyzer': self.analyzer.as_solr_config()
        }

    def __set__(self, obj, val):
        # enforce read-only descriptor
        raise AttributeError


class SolrSchema:
    """Solr schema configuration."""

    #: dictionary of copy fields to be configured
    #: key is source field, value is destination field or list of fields
    copy_fields = {}

    @classmethod
    def get_configuration(cls):
        """Find a SolrSchema subclass for use as schema configuration.
        Currently only supports one schema configuration."""
        subclasses = cls.__subclasses__()
        if not subclasses:
            raise Exception('No Solr schema configuration found')
        elif len(subclasses) > 1:
            raise Exception('Currently only one Solr schema configuration is supported (found %d)' \
                             % len(subclasses))

        return subclasses[0]

    @classmethod
    def get_field_names(cls):
        """iterate over class attributes and return all that are instances of
        :class:`SolrField`"""
        return [attr_name for attr_name, attr_type in cls.__dict__.items()
                if isinstance(attr_type, SolrField)]

    @classmethod
    def get_field_types(cls):
        """iterate over class attributes and return all that are instances of
        :class:`SolrFieldType`"""
        return [attr_name for attr_name, attr_type in cls.__dict__.items()
                if isinstance(attr_type, SolrFieldType)]

    @classmethod
    def configure_fields(cls, solr):
        """Update the configured Solr instance schema to match
        the configured fields.

        Calls :meth:`configure_copy_fields` after
        new fields have been created and before old fields are removed,
        since an outdated copy field could prevent removal.

        :return: :class:`attrdict.AttrDefault` with counts for added,
        updated, and deleted fields.
        """

        current_fields = [field.name for field in solr.schema.list_fields()]
        configured_field_names = cls.get_field_names()

        # use attrdict instead of defaultdict since we have attrmap
        stats = AttrDefault(int, {})

        for field_name in configured_field_names:
            field_opts = getattr(cls, field_name)
            if field_name not in current_fields:
                logger.debug('Adding schema field %s %s', field_name, field_opts)
                solr.schema.add_field(name=field_name, **field_opts)
                stats.added += 1
            else:
                # NOTE: currently no check if field configuration has changed
                logger.debug('Replace schema field %s %s', field_name, field_opts)
                solr.schema.replace_field(name=field_name, **field_opts)
                stats.replaced += 1

        # copy fields need to be configured *after* fields are added
        # but before old fields are removed, because a copy field
        # that references an outdated field will prevent removal
        cls.configure_copy_fields(solr)

        # remove previously defined fields that are no longer current
        for field_name in current_fields:
            # don't remove special fields!
            if field_name == 'id' or field_name.startswith('_'):
                continue
            if field_name not in configured_field_names:
                stats.deleted += 1
                logger.debug('Delete schema field %s', field_name)
                solr.schema.delete_field(field_name)

        return stats

    @classmethod
    def configure_copy_fields(cls, solr):
        """Update configured Solr instance schema with copy fields."""

        # get list of currently configured copy fields
        solr_copy_fields = solr.schema.list_copy_fields()
        # create a dictionary lookup of existing copy fields from Solr
        # source field -> list of destination fields
        cp_fields = AttrDefault(list, {})
        for copyfield in solr_copy_fields:
            cp_fields[copyfield.source].append(copyfield.dest)

        # add copy fields that are not already defined
        for source, dest in cls.copy_fields.items():
            if source not in cp_fields or dest not in cp_fields[source]:
                logger.debug('Adding copy field %s %s', source, dest)
                solr.schema.add_copy_field(source, dest)

        # delete previous copy fields that are no longer wanted
        for cp_field in solr_copy_fields:
            dest = cls.copy_fields.get(cp_field.source, None)
            # check multiple conditions for copy field deletion
            delete = False
            # - source field is not in configured copy fields at all
            if cp_field.source not in cls.copy_fields:
                delete = True
            # - configured destination is a list and value is not present
            elif isinstance(dest, list):
                if cp_field.dest not in dest:
                    delete = True
            # - not a list and value does not match
            elif cp_field.dest != dest:
                delete = True

            if delete:
                logger.debug('Deleting copy field %(source)s %(dest)s', cp_field)
                solr.schema.delete_copy_field(cp_field.source, cp_field.dest)

    @classmethod
    def configure_fieldtypes(cls, solr):
        """Update the configured Solr instance so the schema includes
        the configured field types, if any.

        returns: :class:`attrdict.AttrDefault` with counts for updated
        and added field types."""

        configured_field_types = cls.get_field_types()

        stats = AttrDefault(int, {})

        # if none are configured, nothing to do
        if not configured_field_types:
            return stats

        # convert list return into dictionary keyed on field type name
        current_field_types = {ftype['name']: ftype
                               for ftype in solr.schema.list_field_types()}

        for field_type in configured_field_types:
            field_type_opts = getattr(cls, field_type)
            # add name for comparison with current config
            field_type_opts['name'] = field_type
            if field_type in current_field_types:
                # if field exists [but definition has changed, ] replace it
                # NOTE: could add logic to only update when the field type
                # configuration has changed, but simple dict comparison
                # does not recognize as equal even when the config has
                # not changed
                stats.updated += 1
                logger.debug('Updating field type %s with options %s', field_type, field_type_opts)
                solr.schema.replace_field_type(**field_type_opts)

            # otherwise, create as a new field type
            else:
                stats.added += 1
                logger.debug('Adding field type %s with options %s', field_type, field_type_opts)
                solr.schema.add_field_type(**field_type_opts)

            # NOTE: currently no deletion support; would need to keep
            # a list of predefined Solr field types to check against,
            # which might change, so could be unreliable

        return stats
