from urllib.parse import urljoin
from attrdict import AttrDict

from parasol.solr.client import ClientBase

class Schema(ClientBase):
    """Class for managing Solr schema API."""
    def __init__(self, solr_url, collection, handler, session=None):

        # Go ahead and create a session if one is not passed in
        super().__init__(session=session)
        self.url = self.build_url(solr_url, collection, handler)
        self.headers = {
            'Content-type': 'application/json'
        }

    def _post_field(self, method, **field_kwargs):
        """Post a field definition to the schema API"""
        # Handle situations where we need class as a kwarg
        if 'klass' in field_kwargs:
            field_kwargs['class'] = field_kwargs['klass']
            del field_kwargs['klass']
        data = {
            method: field_kwargs
        }
        self.make_request(
            'post',
            self.url,
            headers=self.headers,
            data=data
        )

    def add_field(self, **field_kwargs):
        """Add a field with the supplied kwargs (or dict as kwargs)"""
        self._post_field('add-field', **field_kwargs)

    def delete_field(self, name):
        """Delete a field with the supplied kwargs (or dict as kwargs)"""
        self._post_field('delete-field', name=name)

    def replace_field(self, **field_kwargs):
        """Replace a field with the supplied kwargs (or dict as kwargs)"""
        # NOTE: Requires a full field definition, no partial updates
        self._post_field('replace-field', **field_kwargs)

    def add_copy_field(self, source, dest, maxChars=None):
        field_definition = {
            'source': source,
            'dest': dest
        }
        if maxChars:
            field_definition['maxChars'] = maxChars
        self._post_field('add-copy-field', **field_definition)

    def delete_copy_field(self, source, dest):
        self._post_field(
                'delete-copy-field',
                **{'source': source, 'dest': dest}
        )

    def add_field_type(self, **field_kwargs):
        """Add a field type to the Solr collection or core."""
        self._post_field('add-field-type', **field_kwargs)

    def delete_field_type(self, name):
       """Delete a field type from the Solr collection or core"""
       self._post_field('delete-field-type', name=name)

    def replace_field_type(self, **field_kwargs):
        """Provide a full definition to replace a field"""
        # NOTE: Requires a full field-type definition, no partial updates
        self._post_field('replace-field-type', **field_kwargs)

    def get_schema(self):
        """Get the full schema for a Solr collection or core."""
        response = self.make_request('get', self.url)
        if response:
            return response.schema

    def list_fields(self, fields=None, includeDynamic=False, showDefaults=False):
        """Get a list of field definitions for a Solr Collection or core."""
        url = urljoin('%s/' % self.url, 'fields')
        params = {}
        if fields:
            params['fl'] = ','.join(fields)
        params['includeDynamic'] = includeDynamic
        params['showDefaults'] = showDefaults
        response = self.make_request('get', url, params=params)
        if response:
            return response.fields

    def list_copy_fields(self, source_fl=None, dest_fl=None):
        url = urljoin('%s/' % self.url, 'copyfields')
        params = {}
        if source_fl:
            params['source.fl'] = ','.join(source_fl)
        if dest_fl:
            params['dest.fl'] = ','.join(dest_fl)
        response = self.make_request('get', url, params=params)
        if response:
            return response.copyFields

    def list_field_types(self, showDefaults=True):
        """List all field types in a Solr collection or core."""
        url = urljoin('%s/' % self.url, 'fieldtypes')
        params = {}
        params['showDefaults'] = showDefaults
        response = self.make_request('get', url, params=params)
        if response:
            return response.fieldTypes




