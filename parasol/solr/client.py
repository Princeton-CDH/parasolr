import inspect
import json
import logging
import sys
import time
from urllib.parse import urljoin

from attrdict import AttrDict
import requests

# Start making Django agnostic from the get-go
try:
    from django.settings import settings
    from django.core.exceptions import ImproperlyConfigured
except ImportError:
    pass


from parasol import __version__ as parasol_version
from parasol.solr.base import ClientBase
from parasol.solr.schema import Schema
from parasol.solr.update import Update
from parasol.solr.admin import CoreAdmin

logger = logging.getLogger(__name__)


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

    def __init__(self, solr_url, collection, session=None):

        # Go ahead and create a session if one is not passed in
        super().__init__(session=session)

        self.solr_url = solr_url
        self.collection = collection
        self.session.headers = {
            'User-Agent': 'Parasol/%s' % parasol_version
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
            headers=headers, params=kwargs)
        if response:
            return response
        return None
