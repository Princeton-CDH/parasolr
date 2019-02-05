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
from parasol.solr.base import ClientBase
from parasol.solr.schema import Schema
from parasol.solr.update import Update
from parasol.solr.admin import CoreAdmin


logger = logging.getLogger(__name__)

class QueryReponse:
    '''Thin wrapper to give access to Solr select responses.'''
    def __init__(self, response):
        self.numFound = response.response.numFound
        self.start = response.response.start
        self.docs = response.response.docs
        self.params = response.responseHeader.params


class SolrClient(ClientBase):
    '''Class to aggregate all of the other Solr APIs and settings.'''

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
    commitWithin = 1000

    def __init__(self, solr_url, collection, commitWithin=None, session=None):
        # Go ahead and create a session if one is not passed in
        super().__init__(session=session)

        self.solr_url = solr_url
        self.collection = collection
        if commitWithin:
            self.commitWithin = commitWithin
        self.session.headers = {
            'User-Agent': 'parasol/%s (python-requests/%s)' % \
                (parasol_version, requests.__version__)
        }

        # attach remainder of API using a common session
        # and common settings
        self.schema = Schema(
                self.solr_url,
                self.collection,
                self.schema_handler,
                self.session
            )
        self.update = Update(
            self.solr_url,
            self.collection,
            self.update_handler,
            self.commitWithin
        )
        self.core_admin = CoreAdmin(
            self.solr_url,
            self.core_admin_handler,
            self.session)

    def query(self, **kwargs):
        '''Perform a query with the specified kwargs and return a response or
        None on error.'''
        url = self.build_url(self.solr_url, self.collection,
                             self.select_handler)
        # use POST for efficiency and send as x-www-form-urlencoded
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        response = self.make_request(
            'post',
            url,
            headers=headers,
            params=kwargs
        )
        if response:
            # queries return the search response for now
            return QueryReponse(response)


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

