import json
from typing import Any, Optional, Union
from urllib.parse import urljoin

import requests

from parasolr.solr.client import ClientBase


class Update(ClientBase):
    """API client for Solr update functionality.

    Args:
        solr_url: Base url for Solr.
        handler: Handler for Update API.
        session: A python-requests :class:`requests.Session`.
    """

    def __init__(
        self,
        solr_url: str,
        collection: str,
        handler: str,
        commitWithin: int,
        session: Optional[requests.Session] = None,
    ) -> None:
        # Go ahead and create a session if one is not passed in
        super().__init__(session=session)
        self.url = self.build_url(solr_url, collection, handler)
        self.headers = {"Content-Type": "application/json"}
        self.params = {"commitWithin": commitWithin}

    def index(
        self, docs: list, commit: bool = False, commitWithin: Optional[int] = None
    ) -> None:
        """Index a document or documents, by default with a soft commit.

        Args:
            docs (list): list of :class:`dict` objects to index.
            commit (bool, optional): Whether or not to make a hard commit to the index.
            commitWithin (int, optional): Override default commitWithin for soft commits.
        """
        params = self.params.copy()
        if commitWithin:
            params["commitWithin"] = commitWithin
        # perform a hard commit, so remove commitWithin as superfluous
        # and set params.
        if commit:
            del params["commitWithin"]
            params["commit"] = True
        url = urljoin("%s/" % self.url, "json/docs")
        self.make_request("post", url, data=docs, params=params, headers=self.headers)

    def _delete(self, del_obj: Union[dict, list]) -> None:
        """Private method to pass a delete object to the update handler.

        Args:
            del_obj: Object to be serialized into valid JSON for Solr delete.
        """
        data = {"delete": del_obj}
        self.make_request(
            "post", self.url, data=data, params=self.params, headers=self.headers
        )

    def delete_by_id(self, id_list: list) -> None:
        """Delete documents by id field.

        Args:
            id_list: A list of ids.
        """
        self._delete(id_list)

    def delete_by_query(self, query: str) -> None:
        """Delete documents by an arbitrary search query.

        Args:
            query: Any valid Solr query.
        """
        self._delete({"query": query})
