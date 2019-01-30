from urllib.parse import urljoin

from attrdict import AttrDict

class CoreAdmin:

    def __init__(self, client):
        self.client = client
        self.url = urljoin('%s/' % client.solr_url, client.core_admin_handler)

    def create(self, name, **kwargs):
        '''Create a new core and register it.'''
        params = {'name': name, 'action': 'CREATE'}
        params.update(kwargs)
        self.client.make_request('get', self.url, params=params)

    def unload(self, core, **kwargs):
        '''Unload a core, without defaults to remove data dir or index.'''
        params = {'core': core, 'action': 'UNLOAD'}
        params.update(kwargs)
        self.client.make_request('get', self.url, params=params)

    def status(self, core='', **kwargs):
        '''Get the status of all cores or no cores.'''
        params = {}
        if core:
            params['core'] = core
        response = self.client.make_request('get', self.url, params=params)
        return AttrDict(
                initFailures=response.initFailures,
                status=response.status
               )