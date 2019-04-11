from collections import OrderedDict
import logging
from typing import Any, Dict, Optional

from attrdict import AttrDict
import requests

from parasolr import __version__ as parasol_version
from parasolr.solr.base import ClientBase
from parasolr.solr.schema import Schema
from parasolr.solr.update import Update
from parasolr.solr.admin import CoreAdmin


logger = logging.getLogger(__name__)


## NOTE: As a rule, Solr parameters that are camelcased are retained that way
# despite not being hugely Pythonic, for consistency with Solr's responses
# and API documentation.

class ParasolrDict(AttrDict):
    """A subclass of :class:`attrdict.AttrDict` that can convert itself to a
    regular dictionary."""

    def as_dict(self):
        """Copy attributes from self as a dictionary, and recursively convert
        instances of :class:`ParasolrDict`."""
        copy = {}
        for k, v in self.items():
            if isinstance(v, ParasolrDict):
                copy[k] = v.as_dict()
            else:
                copy[k] = v
        return copy

class QueryResponse:
    """Thin wrapper to give access to Solr select responses.

    Args:
        response: A Solr query response
    """
    def __init__(self, response: Dict) -> None:
        # cast to ParasolrDict for any dict-like object
        response = ParasolrDict(response)
        self.numFound = int(response.response.numFound)
        self.start = int(response.response.start)
        self.docs = response.response.docs
        self.params = response.responseHeader.params
        self.facet_counts = {}
        if 'docs' in response.response:
            self.docs = response.response.docs
        if 'facet_counts' in response:
            self.facet_counts = \
                self._process_facet_counts(response.facet_counts)
        # NOTE: To access facet_counts.facet_fields or facet_counts.facet_ranges
        # as OrderedDicts, you must use dict notation (or AttrDict *will*
        # convert).

    def _process_facet_counts(self, facet_counts: AttrDict) \
            -> AttrDict:
        """Convert facet_fields and facet_ranges to OrderedDict.

        Args:
          facet_counts: Solr facet_counts field.

        Returns:
          Solr facet_counts field
        """
        if 'facet_fields' in facet_counts:
            for k, v in facet_counts.facet_fields.items():
                facet_counts['facet_fields'][k] = \
                    OrderedDict(zip(v[::2], v[1::2]))
        if 'facet_ranges' in facet_counts:
            for k, v in facet_counts.facet_ranges.items():
               facet_counts['facet_ranges'][k]['counts'] = \
                   OrderedDict(zip(v['counts'][::2], v['counts'][1::2]))
        return facet_counts


class SolrClient(ClientBase):
    """Class to aggregate all of the other Solr APIs and settings.

    Args:
        solr_url: Base url for solr.
        collection: Name of Solr collection or core.
        commitWithin: Time in ms for soft commits to happen.
        session: A python-requests :class:`requests.Session`.
    """

    #: CoreAdmin API handler
    core_admin_handler = 'admin/cores'
    #: Select handler
    select_handler = 'select'
    #: Schema API handler
    schema_handler = 'schema'
    #  Update API handler
    update_handler = 'update'
    #: core or collection name
    collection = ''
    #: commitWithin time in ms
    commitWithin = 1000


    def __init__(self, solr_url: str, collection: str,
                 commitWithin: Optional[int] = None,
                 session: Optional[requests.Session] = None) -> None:
        # Go ahead and create a session if one is not passed in
        super().__init__(session=session)

        self.solr_url = solr_url
        self.collection = collection
        if commitWithin:
            self.commitWithin = commitWithin
        self.session.headers = {
            'User-Agent': 'parasolr/%s (python-requests/%s)' % \
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

    def query(self, wrap: bool = True, **kwargs: Any) -> Optional[QueryResponse]:
        """Perform a query with the specified kwargs.

        Args:
            **kwargs: Any valid Solr search parameters.

        Returns:
            A search QueryResponse.
        """
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
            return QueryResponse(response) if wrap else response
