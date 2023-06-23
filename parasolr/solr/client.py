import logging
from collections import OrderedDict
from typing import Any, Dict, List, Optional

import requests
from addict import Dict as AttrDict

from parasolr import __version__ as parasol_version
from parasolr.solr.admin import CoreAdmin
from parasolr.solr.base import ClientBase
from parasolr.solr.schema import Schema
from parasolr.solr.update import Update

logger = logging.getLogger(__name__)


# NOTE: As a rule, Solr parameters that are camelcased are retained that way
# despite not being hugely Pythonic, for consistency with Solr's responses
# and API documentation.


class ParasolrDict(AttrDict):
    """A subclass of :class:`addict.Dict` that can convert itself to a
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

    def __repr__(self):
        """Print a dict-like :meth:`repr`, without including 'addict.Dict'."""
        return "ParasolrDict(%s)" % super(AttrDict, self).__repr__()


class BaseResponse:
    """Base Solr response class with fields common to standard and
    grouped results."""

    def __init__(self, response: Dict) -> None:
        # cast to ParasolrDict for any dict-like object and store
        self.response = ParasolrDict(response)
        # facet counts need to be processed to convert into
        # ordered dict, so process and store
        self.facet_counts = {}
        if "facet_counts" in self.response:
            self.facet_counts = self._process_facet_counts(response.facet_counts)

        # NOTE: To access facet_counts.facet_fields or facet_counts.facet_ranges
        # as OrderedDicts, you must use dict notation (or AttrDict *will*
        # convert).

    @property
    def params(self):
        "parameters sent to solr in the request, as returned in response header"
        return self.response.responseHeader.params

    @property
    def stats(self):
        "stats portion of the response, if statics were requested"
        return self.response.get("stats", {})

    @property
    def highlighting(self):
        "highlighting portion of the response, if highlighting was requested"
        return self.response.get("highlighting", {})

    @property
    def expanded(self):
        "expanded portion of the response, if collapse/expanded results enabled"
        return self.response.get("expanded", {})

    def _process_facet_counts(self, facet_counts: AttrDict) -> OrderedDict:
        """Convert facet_fields and facet_ranges to OrderedDict.

        Args:
          facet_counts: Solr facet_counts field.

        Returns:
          Solr facet_counts field
        """
        if "facet_fields" in facet_counts:
            for k, v in facet_counts.facet_fields.items():
                facet_counts["facet_fields"][k] = OrderedDict(zip(v[::2], v[1::2]))
        if "facet_ranges" in facet_counts:
            for k, v in facet_counts.facet_ranges.items():
                facet_counts["facet_ranges"][k]["counts"] = OrderedDict(
                    zip(v["counts"][::2], v["counts"][1::2])
                )
        return facet_counts


class QueryResponse(BaseResponse):
    """Thin wrapper to give access to Solr select responses.

    Args:
        response: A Solr query response
    """

    def __init__(self, response: Dict) -> None:
        super().__init__(response)
        # document list is contained with the "response" element
        # in the json returned by solr
        self.document_list = self.response.response

    @property
    def numFound(self) -> int:
        return self.document_list.numFound

    @property
    def start(self) -> int:
        return self.document_list.start

    @property
    def docs(self) -> List:
        return self.document_list.docs

    @property
    def items(self) -> List:
        return self.docs


class GroupedResponse(BaseResponse):
    """Query response variant for grouped results.

    Args:
        response: A Solr query response
    """

    def __init__(self, response: Dict) -> None:
        super().__init__(response)
        # grouped response structure is structured as a dict
        # first keyed on fieldname with number of matches, then a dict
        # of group values and corresponding document list
        self.grouped = self.response.grouped

        # access grouped results at:
        # self.grouped.fieldname.groups
        # groups has
        # will be a dict of field value, doclist

    @property
    def group_field(self) -> str:
        "group.field as stored in the params. Not yet supporting grouping by query."
        return self.params.get("group.field", "")

    @property
    def numFound(self) -> int:
        # each field used for grouping has a total
        # for the number of matches in that grouping
        # return sum(group["matches"] for group in self.grouped.values())
        return self.grouped.get(self.group_field, {}).get("matches", 0)

    @property
    def groups(self) -> List:
        """Unlike `QueryResponse.docs`, this returns a list of groups with nested documents.

        :return: _description_
        :rtype: List
        """
        return self.grouped.get(self.group_field, {}).get("groups", [])

    @property
    def items(self) -> List:
        return self.groups


class SolrClient(ClientBase):
    """Class to aggregate all of the other Solr APIs and settings.

    Args:
        solr_url: Base url for solr.
        collection: Name of Solr collection or core.
        commitWithin: Time in ms for soft commits to happen.
        session: A python-requests :class:`requests.Session`.
    """

    #: CoreAdmin API handler
    core_admin_handler = "admin/cores"
    #: Select handler
    select_handler = "select"
    #: Schema API handler
    schema_handler = "schema"
    #  Update API handler
    update_handler = "update"
    #: core or collection name
    collection = ""
    #: commitWithin time in ms
    commitWithin = 1000

    def __init__(
        self,
        solr_url: str,
        collection: str,
        commitWithin: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        # Go ahead and create a session if one is not passed in
        super().__init__(session=session)

        self.solr_url = solr_url
        self.collection = collection
        if commitWithin:
            self.commitWithin = commitWithin
        self.session.headers = {
            "User-Agent": "parasolr/%s (python-requests/%s)"
            % (parasol_version, requests.__version__)
        }

        # attach remainder of API using a common session
        # and common settings
        self.schema = Schema(
            self.solr_url, self.collection, self.schema_handler, self.session
        )
        self.update = Update(
            self.solr_url, self.collection, self.update_handler, self.commitWithin
        )
        self.core_admin = CoreAdmin(
            self.solr_url, self.core_admin_handler, self.session
        )

    def query(self, wrap: bool = True, **kwargs: Any) -> Optional[QueryResponse]:
        """Perform a query with the specified kwargs.

        Args:
            **kwargs: Any valid Solr search parameters.

        Returns:
            A search QueryResponse.
        """
        url = self.build_url(self.solr_url, self.collection, self.select_handler)
        # use POST for efficiency and send as x-www-form-urlencoded
        headers = {"content-type": "application/x-www-form-urlencoded"}
        response = self.make_request("post", url, headers=headers, params=kwargs)
        if response:
            # queries return the search response for now

            # unnless a raw/unwrapped result is requested,
            # determine result type to use and initialize
            if wrap:
                result_class = QueryResponse
                if "grouped" in response:
                    result_class = GroupedResponse
                response = result_class(response)

            return response
