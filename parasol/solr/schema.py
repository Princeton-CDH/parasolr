class Schema:

    def __init__(self, client):

        self.client = client
        self.url = self.client._build_url(client.schema_handler)
        self.headers = {
            'Content-type': 'application/json'
        }
        self.params = {
            ''
        }

    def add_field(self, **field_kwargs):
        data = {
            'add-field': field_kwargs
        }
        self.client._make_request(
                'post',
                self.url,
                headers=self.headers,
                data=data
        )

    def delete_field(self, name):
        data = {
            'delete-field': name
        }
        self.client._make_request(
            'post',
            self.url,
            headers=self.headers,
            data=data
        )

    def replace_field(self, **field_kwargs):
        data = {
            'replace-field': field_kwargs
        }
        self.client._make_request(
            'post', self.url,
            headers=self.headers,
            data=data
        )