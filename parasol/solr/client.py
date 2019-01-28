import inspect
import json
import logging
import sys
import time
from urllib.parse import urljoin

import requests

from parasol import __version__ as parasol_version
from parasol.solr.schema import Schema
from parasol.solr.update import Update

logger = logging.getLogger(__name__)


class SolrClient:

    #: Url for solr core instance
    solr_url = 'http://localhost:8983/solr'
    #: select handler
    select_handler = 'select'
    #: schema handler
    schema_handler = 'schema'
    # update handler
    update_handler = 'update'
    #: core or collection
    core = ''


    def __init__(self, *args, **kwargs):
        # For now, a generous init that will override valuesbut not
        # choke on an unexpected one.
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Don't allow session configuration to be so easily overwritten
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Parasol/%s' % parasol_version
        }

        self.schema = Schema(self)
        self.update = Update(self)

    def _build_url(self, handler):
        '''Return a url to a handler'''
        # Two step proecess to avoid quirks in urljoin behavior
        # First, join the core with a slashes appended just in case so
        # it doesn't ovewrite the base url (extras cause no issues)
        core = urljoin('%s/' % self.solr_url, '%s/' % self.core)
        # then return the core joined with handler -- without slash per
        # Solr API docs.
        return urljoin(core, handler)

    def _make_request(self, meth, url, headers={},
                      params={}, data=None, **kwargs):
        if 'wt' not in params:
            params.update({'wt': 'json'})
        start = time.time()
        response = self.session.request(
                meth,
                url,
                params=params,
                headers=headers,
                data=json.dumps(data),
                **kwargs)
        total_time = time.time() - start
        log_string = '%s %s=>%d: %f sec' % \
            (meth.upper(), url, response.status_code, total_time)
        if response.status_code == requests.codes.ok:
            logger.debug(log_string)
            print(response.json())
            return response
        logger.error(log_string)

    def query(self, **kwargs):
        '''Perform a query with the specified kwargs and return a '''
        url = self._build_url(self.select_handler)
        # use POST for efficiency and send as x-www-form-urlencoded
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        response = self._make_request('post', url, headers=headers, params=kwargs)
        if response:
            return response.json()

