import json
import logging
import time
from urllib.parse import urljoin

from attrdict import AttrDict
import requests


logger = logging.getLogger(__name__)


class SolrClientException(Exception):
    """Base class for all exceptions in this module"""
    pass


class CoreExists(SolrClientException):
    """Raised when default core for running unit tests exists"""
    pass


class ClientBase:
    """Base object with common communication methods for talking to Solr API."""

    def __init__(self, session=None):
        if session is None:
            self.session = requests.Session()
        else:
            self.session = session


    def build_url(self, solr_url, collection, handler):
        """Return a url to a handler based on core and base url"""
        # Two step proecess to avoid quirks in urljoin behavior
        # First, join the collection/core with a slashes appended
        # just in case so # it doesn't ovewrite the base url
        # (extras cause no issues)
        collection = urljoin('%s/' % solr_url, '%s/' % collection)
        # then return the core joined with handler -- without slash per
        # Solr API docs.
        return urljoin(collection, handler)

    def make_request(self, meth, url, headers=None,
                      params=None, data=None, **kwargs):
        """Private method for making a request to Solr, wraps session.request"""
        if params is None:
            params = dict()
            # always add wt=json for JSON api
        params['wt'] = 'json'
        # convert True and False to their appropriate string values for
        # query string to Solr
        for key, value in params.items():
            if value is True:
                params[key] = 'true'
            if value is False:
                params[key] = 'false'
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
        # log the url call and speed regardless
        logger.debug(
            '%s %s=>%d: %f sec',
            meth.upper(),
            url,
            response.status_code,
            total_time
        )
        if response.status_code != requests.codes.ok:
                # Add the content of the response on the off chance
                # it's helpful
                logger.error(
                    '%s %s=> err: %s',
                    meth.upper(),
                    url,
                    response.content,
                )
                # return None for failure
                return
        # do further error checking on the response because Solr
        # may return 200 but pass along its own error codes and information
        output = AttrDict(response.json())
        if 'responseHeader' in output \
                and output.responseHeader.status != 0:
            logger.error(
                '%s %s => %d: %s',
                meth.upper(),
                url,
                output.responseHeader.status,
                output.responseHeader.errors
            )
            # return None for failure
            return

        return AttrDict(response.json())
