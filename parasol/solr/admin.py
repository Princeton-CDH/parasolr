from urllib.parse import urljoin

from attrdict import AttrDict

from parasol.solr.client import ClientBase

class CoreAdmin(ClientBase):
    '''API client for Solr core admin.'''
    def __init__(self, solr_url, handler, session=None):

        super().__init__(session=session)
        self.url = urljoin('%s/' % solr_url, handler)

    def create(self, name, **kwargs):
        '''Create a new core and register it.'''
        params = {'name': name, 'action': 'CREATE'}
        params.update(kwargs)
        self.make_request('get', self.url, params=params)

    def unload(self, core, **kwargs):
        '''Unload a core, without defaults to remove data dir or index.'''
        params = {'core': core, 'action': 'UNLOAD'}
        params.update(kwargs)
        self.make_request('get', self.url, params=params)

    def status(self, core='', **kwargs):
        '''Get the status of all cores or one core.'''
        params = {}
        if core:
            params['core'] = core
        response = self.make_request('get', self.url, params=params)
        return AttrDict(
                initFailures=response.initFailures,
                status=response.status
               )