from typing import Any, Optional
from urllib.parse import urljoin

import requests
from attrdict import AttrDict

from parasolr.solr.base import ClientBase, SolrConnectionNotFound


class CoreAdmin(ClientBase):
    """API client for Solr core admin.

    Args:
        solr_url: Base url for Solr.
        handler: Handler for CoreAdmin API
        session: A python-requests :class:`requests.Session`
    """

    def __init__(
        self, solr_url: str, handler: str, session: Optional[requests.Session] = None
    ) -> None:
        super().__init__(session=session)
        self.solr_url = solr_url
        self.url = urljoin("%s/" % solr_url, handler)

    def create(self, name: str, **kwargs: Any) -> None:
        """Create a new core and register it.

        Args:
          name: Name of core to create.
          **kwargs: Any valid parameter for core creation in Solr.
        """
        params = {"name": name, "action": "CREATE"}
        params.update(kwargs)
        self.make_request("get", self.url, params=params)

    def unload(self, core: str, **kwargs: Any) -> None:
        """Unload a core, without defaults to remove data dir or index.

        Args:
          core: Name of core to unload.
          **kwargs: Any valid parameter for core unload in Solr.
        """
        params = {"core": core, "action": "UNLOAD"}
        params.update(kwargs)
        self.make_request("get", self.url, params=params)

    def reload(self, core: str) -> None:
        """Reload a Solr Core.

        Args:
          core: Name of core to reload.
        """
        params = {"core": core, "action": "RELOAD"}
        return self.make_request("get", self.url, params=params)

    def status(self, core: str = None) -> Optional[AttrDict]:
        """Get the status of all cores or one core.

        Args:
          core: Name of core to get status.
        """
        params = {}
        if core:
            params["core"] = core
        response = self.make_request("get", self.url, params=params)
        if response:
            return AttrDict(initFailures=response.initFailures, status=response.status)

    def ping(self, core: str) -> bool:
        """Ping a core to check status.

        Args:
          core: Name of core to ping.

        Returns:
          True if core status is OK, otherwise False.

        """
        ping_url = "/".join([self.solr_url.rstrip("/"), core, "admin", "ping"])
        # ping returns 404 if core does not exist, but that's ok here
        allowed_responses = [requests.codes.ok, requests.codes.not_found]
        try:
            response = self.make_request(
                "get", ping_url, allowed_responses=allowed_responses
            )
            # return True if response is valid and status is OK
            return response and response.status == "OK"
        except SolrConnectionNotFound:
            return False
