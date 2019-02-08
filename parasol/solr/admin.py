from urllib.parse import urljoin

from attrdict import AttrDict
import requests

from parasol.solr.client import ClientBase


class CoreAdmin(ClientBase):
    """API client for Solr core admin."""
    def __init__(self, solr_url, handler, session=None):
        """
        :param solr_url: Base url for Solr.
        :type solr_url: str
        :param handler: Handler for CoreAdmin API.
        :type handler: str
        :param session: A python-requests Session.
        :type session: :class:`requests.Session`
        """

        super().__init__(session=session)
        self.solr_url = solr_url
        self.url = urljoin('%s/' % solr_url, handler)

    def create(self, name, **kwargs):
        """Create a new core and register it.

        :param name: Name of core to create.
        :type name: str
        :param kwargs: Any valid parameter for core creation in Solr.
        """
        params = {'name': name, 'action': 'CREATE'}
        params.update(kwargs)
        self.make_request('get', self.url, params=params)

    def unload(self, core, **kwargs):
        """Unload a core, without defaults to remove data dir or index.

        :param core: Name of core to unload.
        :type core: str
        :param kwargs: Any valid parameter for core unload in Solr.
        """
        params = {'core': core, 'action': 'UNLOAD'}
        params.update(kwargs)
        self.make_request('get', self.url, params=params)

    def reload(self, core):
        """Reload a Solr Core.

        :param core: Name of core to reload.
        :type core: str
        """
        params = {'core': core, 'action': 'RELOAD'}
        return self.make_request('get', self.url, params=params)

    def status(self, core=''):
        """Get the status of all cores or one core.

        :param core: Name of core to get status.
        :type core: str
        """
        params = {}
        if core:
            params['core'] = core
        response = self.make_request('get', self.url, params=params)
        return AttrDict(
            initFailures=response.initFailures,
            status=response.status
        )

    def ping(self, core):
        """Ping a core to check status.

        :param core: Name of core to ping.
        :type core: str

        :returns: True if core status is OK, otherwise False.
        """
        ping_url = '/'.join([self.solr_url.rstrip('/'), core, 'admin', 'ping'])
        response = self.make_request('get', ping_url)
        # ping returns 404 if core does not exist (make request returns None)

        # return True if response is valid and status is OK
        return response and response.status == 'OK'
