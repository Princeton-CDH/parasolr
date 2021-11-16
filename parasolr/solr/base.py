import json
import logging
import time
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from attrdict import AttrDict

logger = logging.getLogger(__name__)


class SolrClientException(Exception):
    """Base class for all exceptions in this module"""


class CoreExists(SolrClientException):
    """Raised when a Solr core exists and it should not."""


class ImproperConfiguration(SolrClientException):
    """Raised when a required setting is not present or is an invalid value."""


class SolrConnectionNotFound(SolrClientException):
    """Raised when a 404 is returned from Solr (e.g., attempting to query
    a non-existent collection on a valid Solr server)"""


class ClientBase:
    """Base object with common communication methods for talking to Solr API.

    Args:
        session: A python-requests :class:`requests.Session`.
    """

    def __init__(self, session: requests.Session = None):
        if session is None:
            self.session = requests.Session()
        else:
            self.session = session

    def build_url(self, solr_url: str, collection: str, handler: str) -> str:
        """Return a url to a handler based on core and base url.

        Args:
            solr_url: Base url for Solr.
            collection: Collection or core name.
            handler: Handler URL for construction.

        Returns:
            A full-qualified URL.
        """
        # Two step proecess to avoid quirks in urljoin behavior
        # First, join the collection/core with a slashes appended
        # just in case so # it doesn't ovewrite the base url
        # (extras cause no issues)
        collection = urljoin("%s/" % solr_url, "%s/" % collection)
        # then return the core joined with handler -- without slash per
        # Solr API docs.
        return urljoin(collection, handler)

    def make_request(
        self,
        meth: str,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        wrap: bool = True,
        allowed_responses: Optional[list] = None,
        **kwargs: Any
    ) -> Optional[AttrDict]:
        """Make an HTTP request to Solr. May optionally specify a list of
        allowed HTTP status codes for this request. Responses will be
        logged as errors if they are not in the list, but only responses
        with 200 OK status will be loaded as JSON.

        Args:
            meth: HTTP method to use.
            url: URL to make request to.
            headers: HTTP headers.
            params: Params to use as form-fields or query-string params.
            data: Data for a POST request.
            allowed_responses: HTTP status codes that are allowed for this
                request; if not set, defaults to 200 OK
            **kwargs: Any other kwargs for the request.
        """

        if params is None:
            params = dict()
            # always add wt=json for JSON api

        # copy user-supplied params for inclusion in debug logging
        user_params = params.copy()
        params["wt"] = "json"
        # convert True and False to their appropriate string values for
        # query string to Solr
        for key, value in params.items():
            if value is True:
                params[key] = "true"
            if value is False:
                params[key] = "false"
        start = time.time()
        response = self.session.request(
            meth, url, params=params, headers=headers, data=json.dumps(data), **kwargs
        )
        # log the url call and speed regardless
        logger.debug(
            "%s %s => %d: %f sec%s",
            meth.upper(),
            url,
            response.status_code,
            time.time() - start,
            "\n%s" % user_params if user_params else "",
        )

        if allowed_responses is None:
            allowed_responses = [requests.codes.ok]

        # 404 error should be escalated, since it likely means a
        # misconfiguration (wrong core name or core not created)
        if response.status_code == requests.codes.not_found:
            raise SolrConnectionNotFound("404 Not Found: %s" % url)

        if response.status_code not in allowed_responses:
            # Add the content of the response on the off chance
            # it's helpful
            logger.error(
                "%s %s=> err: %s",
                meth.upper(),
                url,
                response.content,
            )
            # return None for failure
            return

        # do further error checking on the response because Solr
        # may return 200 but pass along its own error codes and information

        # if response was allowed but not a 200, just
        # return response instead of attempting to load as json
        if response.status_code != requests.codes.ok:
            return response

        output = AttrDict(response.json())
        if "responseHeader" in output and output.responseHeader.status != 0:
            logger.error(
                "%s %s => %d: %s",
                meth.upper(),
                url,
                output.responseHeader.status,
                output.responseHeader.errors,
            )
            # return None for failure
            return

        if wrap:
            return output

        return response.json()
