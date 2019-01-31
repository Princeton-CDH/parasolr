import inspect
import json
import logging
import sys
import time
from urllib.parse import urljoin

from attrdict import AttrDict
import requests

# provide Django integration Django if installed
try:
    import django
    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured
except ImportError:
    django = None


from parasol import __version__ as parasol_version
from parasol.solr.schema import Schema
from parasol.solr.update import Update
from parasol.solr.admin import CoreAdmin

logger = logging.getLogger(__name__)



class SolrClientException(Exception):
    '''Base class for all exceptions in this module'''
    pass


class CoreForTestExists(SolrClientException):
    '''Raised when default core for running unit tests exists'''


class SolrClient:
    '''Base class for all SolrClient with sane development defaults'''
    #: Url for solr base instance
    solr_url = 'http://localhost:8983/solr'
    #: core admin handler
    core_admin_handler = 'admin/cores'
    #: select handler
    select_handler = 'select'
    #: schema handler
    schema_handler = 'schema'
    # update handler
    update_handler = 'update'
    #: core or collection
    collection = ''
    # commitWithin definition
    commit_within = 1000

    def __init__(self, url, collection='', *args, **kwargs):
        # For now, a generous init that will override valuesbut not
        # choke on an unexpected one.
        self.url = url
        self.collection = collection
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Don't allow session configuration to be so easily overwritten
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Parasol/%s' % parasol_version
        }

        self.schema = Schema(self)
        self.update = Update(self, commitWithin=1000)
        self.core_admin = CoreAdmin(self)

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
        '''Private method for making a request to Solr, wraps session.request'''
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
            # do further error checking on the response because Solr
            # may return 200 but pass along its own error codes and information
            output = AttrDict(response.json())
            if 'responseHeader' in output \
                    and output.responseHeader.status != 0:
                log_string = (
                    '%s %s (%d): %s' %
                    meth.upper(),
                    url,
                    output.responseHeader.status,
                    output.responseHeader.status
                )
                logger.error(log_string)
                return None
            return AttrDict(response.json())
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


if django:

    class DjangoSolrClient(SolrClient):
        ''':class:`SolrClient` subclass that automatically pulls configuration
        from django settings.  Expected configuration format:

            SOLR_CONNECTIONS = {
                'default': {
                    'URL': 'http://localhost:8983/solr/',
                    'COLLECTION': 'mycore'
                }
            }

        Collection can be omitted when connecting to a single-core Solr
        instance.
        '''

        def __init__(self, *args, **kwargs):
            solr_opts = getattr(settings, 'SOLR_CONNECTIONS', None)
            # no solr connection section at all
            if not solr_opts:
                raise ImproperlyConfigured('DjangoSolrClient requires SOLR_CONNECTIONS in settings')

            default_solr = solr_opts.get('default', None)
            # no default config
            if not default_solr:
                raise ImproperlyConfigured('No "default" in SOLR_CONNECTIONS configuration')

            url = default_solr.get('URL', None)
            # URL is required
            if not url:
                raise ImproperlyConfigured('No URL in default SOLR_CONNECTIONS configuration')

            collection = default_solr.get('COLLECTION', '')
            logger.debug('Connecting to default Solr %s%s', url, collection)
            super().__init__(url, collection)
