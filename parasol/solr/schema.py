"""
Module with class and methods for the Solr Schema API.
"""


from urllib.parse import urljoin

from parasol.solr.client import ClientBase

class Schema(ClientBase):
    """Class for managing Solr Schema API"""
    def __init__(self, solr_url, collection, handler, session=None):
        """
        :param solr_url: Base url for Solr.
        :type name: str
        :param collection: Name of the collection or core.
        :type collection: str
        :param handler: Handler name for Solr Schema API.
        :type handler: str
        :param session: A python-requests Session.
        :type session: :class:`requests.Session`.
        """
        # Go ahead and create a session if one is not passed in
        super().__init__(session=session)
        self.url = self.build_url(solr_url, collection, handler)
        self.headers = {
            'Content-type': 'application/json'
        }

    def _post_field(self, method, **field_kwargs):
        """Post a field definition to the schema API.

        :param method: Solr field method to use.
        :type method: str
        :param field_kwargs: Field arguments to use in definition.

        :Field kwargs:
            Note: Any valid schema definition may be used; if passed as
            ``kwargs``, rather than :class:`dict`, ``klass`` may be used
            instead of ``class``.
        """
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
        """Add a field with the supplied definition.

        :param field_kwargs: Any valid Solr field definition values.
        """
        self._post_field('add-field', **field_kwargs)

    def delete_field(self, name):
        """Delete a field with the supplied name.

        :param name: Name of field to delete.
        :type name: str
        """
        self._post_field('delete-field', name=name)

    def replace_field(self, **field_kwargs):
        """Replace a field with the supplied definition

        :param field_kwargs: Any valid Solr field definition values.

        :Note:
            This must be a full redefinition, not a partial update.
        """
        self._post_field('replace-field', **field_kwargs)

    def add_copy_field(self, source, dest, maxChars=None):
        """Add a copy field between two existing fields.

        :param source: Source Solr field.
        :type source: str
        :param dest: Destination Solr field.
        :type dest: str
        :param maxChars: Maximum characters to copy.
        :type maxChars: int
        """
        field_definition = {
            'source': source,
            'dest': dest
        }
        if maxChars:
            field_definition['maxChars'] = maxChars
        self._post_field('add-copy-field', **field_definition)

    def delete_copy_field(self, source, dest):
        """Delete a Solr copy field.

        :param source: Source Solr field.
        :type source: str
        :param dest: Destination Solr field.
        """
        self._post_field(
            'delete-copy-field',
            **{'source': source, 'dest': dest}
        )

    def add_field_type(self, **field_kwargs):
        """Add a field type to a Solr collection or core.

        :param field_kwargs: Any valid Solr field definition values.
        """
        self._post_field('add-field-type', **field_kwargs)

    def delete_field_type(self, name):
       """Delete a field type from a Solr collection or core.

       :param name: Name of Solr field type to delete.
       :type name: str
       """
       self._post_field('delete-field-type', name=name)

    def replace_field_type(self, **field_kwargs):
        """Replace a field type from a Solr collection or core.

        :param field_kwargs: Any valid Solr field definition values.

        :Note:
            This must be a full redefinition, not a partial update.
        """
        self._post_field('replace-field-type', **field_kwargs)

    def get_schema(self):
        """Get the full schema for a Solr collection or core.

        :return: Schema as returned by Solr.
        :rtype: :class:`attrdict.AttrDict`
        """
        response = self.make_request('get', self.url)
        if response:
            return response.schema

    def list_fields(self, fields=None, includeDynamic=False, showDefaults=False):
        """Get a list of field definitions for a Solr Collection or core.

        :param fields: A list of fields to filter by.
        :type fields: list
        :param includeDynamic: Include Solr dynamic fields in search.
        :type includeDynamic: bool
        :param showDefaults: Show default Solr fields.
        :type showDefaults: bool

        :return: list of fields as returned by Solr.
        :rtype: list
        """
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
        """Return a list of copy fields from Solr.
        :param source_fl: Source field to filter by.
        :type source_fl: str
        :param dest_fl: Destination field to filter by.
        :type dest_fl: str

        :return: list of copy fields as returned by Solr.
        :rtype: list
        """
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
        """List all field types in a Solr collection or core.
        :param showDefaults: Show default fields (defaults to True).
        :type showDefaults: bool:

        :return: list of copy fields as returned by Solr.
        :rtype: list
        """
        url = urljoin('%s/' % self.url, 'fieldtypes')
        params = {}
        params['showDefaults'] = showDefaults
        response = self.make_request('get', url, params=params)
        if response:
            return response.fieldTypes
