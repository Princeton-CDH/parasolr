class Schema:
    '''Class for managing Solr schema API.'''
    def __init__(self, client):

        self.client = client
        self.url = self.client.build_url(client.schema_handler)
        self.headers = {
            'Content-type': 'application/json'
        }

    def _post_field(self, method, **field_kwargs):
        '''Post a field definition to the schema API'''
        data = {
            method: field_kwargs
        }
        self.client.make_request(
            'post',
            self.url,
            headers=self.headers,
            data=data
        )

    def add_field(self, **field_kwargs):
        '''Add a field with the supplied kwargs (or dict as kwargs)'''
        self._post_field('add-field', **field_kwargs)

    def delete_field(self, name):
        '''Delete a field with the supplied kwargs (or dict as kwargs)'''
        self._post_field('delete-field', name=name)

    def replace_field(self, **field_kwargs):
        '''Replace a field with the supplied kwargs (or dict as kwargs)'''
        # NOTE: Requires a full field definition, no partial updates
        self._post_field('replace-field', **field_kwargs)

    def add_field_type(self, **field_kwargs):
        '''Add a field type to the Solr collection or core.'''
        self._post_field('add-field-type', **field_kwargs)

    def delete_field_type(self, **field_kwargs):
       '''Delete a field type from the Solr collection or core'''
       self._post_field('delete-field-type', name=name)

    def replace_field_type(self, **field_kwargs):
        '''Provide a full definition to replace a field'''
        self._post_field('replace-field-type', **field_kwargs)

