import inspect
import json
import logging
import sys
import time
from urllib.parse import urljoin

import requests

# Start making Django agnostic from the get-go
try:
    from django.settings import settings
    from django.core.exceptions import ImproperlyConfigured
except ImportError:
    settings = {}


from parasol import __version__ as parasol_version
from parasol.solr.schema import Schema
from parasol.solr.update import Update

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class SolrClient:
    '''Base class for all SolrClient with sane development defaults'''
    #: Url for solr base instance
    solr_url = 'http://localhost:8983/solr'
    #: select handler
    select_handler = 'select'
    #: schema handler
    schema_handler = 'schema'
    # update handler
    update_handler = 'update'
    #: core or collection
    collection = ''

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

    def build_url(self, handler):
        '''Return a url to a handler based on core and base url'''
        # Two step proecess to avoid quirks in urljoin behavior
        # First, join the collection/core with a slashes appended
        # just in case so # it doesn't ovewrite the base url
        # (extras cause no issues)
        collection = urljoin('%s/' % self.solr_url, '%s/' % self.collection)
        # then return the core joined with handler -- without slash per
        # Solr API docs.
        return urljoin(collection, handler)

    def make_request(self, meth, url, headers={},
                      params={}, data=None, **kwargs):
        '''Private method for making a request to Solr, wraps session.request.all'''
        # always add wt=json for JSON api
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
        # log the time as needed
        total_time = time.time() - start
        log_string = '%s %s=>%d: %f sec' % \
            (meth.upper(), url, response.status_code, total_time)
        if response.status_code == requests.codes.ok:
            logger.debug(log_string)
            # do further error checking on the response
            output = response.json()
            if 'responseHeader' in output \
                    and output['responseHeader']['status'] != 0:
                log_string = (
                    '%s %s (%d): %s' %
                    meth.upper(),
                    url,
                    output['responseHeader']['status'],
                    output['responseHeader']['errors']
                )
                logger.debug(log_string)
                return None
            return response
        logger.error(log_string)

    def query(self, **kwargs):
        '''Perform a query with the specified kwargs and return a response or
        None on error.'''
        url = self.build_url(self.select_handler)
        # use POST for efficiency and send as x-www-form-urlencoded
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        response = self.make_request(
            'post',
            url,
            headers=headers, params=kwargs)
        if response:
            return response.json()
        return None
