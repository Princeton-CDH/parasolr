"""
Module with class and methods for the Solr Schema API.
"""
from typing import Any, List, Optional
from urllib.parse import urljoin

import requests
from attrdict import AttrDict

from parasolr.solr.client import ClientBase


class Schema(ClientBase):
    """Class for managing Solr Schema API

    Args:
        solr_url: Base url for Solr.
        collection: Name of the collection or core.
        handler: Handler name for Solr Schema API.
        session: A python-requests :class:`requests.Session`.
    """

    def __init__(
        self,
        solr_url: str,
        collection: str,
        handler: str,
        session: requests.Session = None,
    ):
        # Go ahead and create a session if one is not passed in
        super().__init__(session=session)
        self.url = self.build_url(solr_url, collection, handler)
        self.headers = {"Content-type": "application/json"}

    def _post_field(self, method: str, **field_kwargs: Any) -> None:
        """Post a field definition to the schema API.

        Args:
          method: Solr field method to use.
          **field_kwargs: Field arguments to use in definition. Any valid schema
            definition may be used; if passed as ``kwargs``, rather than
            :class:`dict`, ``klass`` may be used instead of ``class``.
        """
        # Handle situations where we need class as a kwarg
        if "klass" in field_kwargs:
            field_kwargs["class"] = field_kwargs["klass"]
            del field_kwargs["klass"]
        data = {method: field_kwargs}
        self.make_request("post", self.url, headers=self.headers, data=data)

    def add_field(self, **field_kwargs: Any) -> None:
        """Add a field with the supplied definition.

        Args:
          **field_kwargs: Any valid Solr field definition values.
        """
        self._post_field("add-field", **field_kwargs)

    def delete_field(self, name: str) -> None:
        """Delete a field with the supplied name.

        Args:
          name: Name of field to delete.
        """
        self._post_field("delete-field", name=name)

    def replace_field(self, **field_kwargs: Any) -> None:
        """Replace a field with the supplied definition

        Args:
          **field_kwargs: Any valid Solr field definition values; must be a
            full redefinition, not a partial update.
        """
        self._post_field("replace-field", **field_kwargs)

    def add_copy_field(self, source: str, dest: str, maxChars: int = None) -> None:
        """Add a copy field between two existing fields.

        Args:
            source: Source Solr field.
            dest: Destination Solr field.
            maxChars: Maximum characters to copy.
        """
        field_definition = {"source": source, "dest": dest}
        if maxChars:
            field_definition["maxChars"] = maxChars
        self._post_field("add-copy-field", **field_definition)

    def delete_copy_field(self, source: str, dest: str) -> None:
        """Delete a Solr copy field.

        Args:
            source: Source Solr field.
            dest: Destination Solr field.
        """
        self._post_field("delete-copy-field", **{"source": source, "dest": dest})

    def add_field_type(self, **field_kwargs: Any) -> None:
        """Add a field type to a Solr collection or core.

        Args:
            **field_kwargs: Any valid Solr field definition values.

        Returns:
            None
        """
        self._post_field("add-field-type", **field_kwargs)

    def delete_field_type(self, name: str) -> None:
        """Delete a field type from a Solr collection or core.

        Args:
            name: Name of Solr field type to delete.
        """
        self._post_field("delete-field-type", name=name)

    def replace_field_type(self, **field_kwargs: Any) -> None:
        """Replace a field type from a Solr collection or core.

        Args:
            **field_kwargs: Any valid Solr field definition values, but
                must be a full redefinition, not a partial update.
        """
        self._post_field("replace-field-type", **field_kwargs)

    def get_schema(self) -> AttrDict:
        """Get the full schema for a Solr collection or core.

        Returns:
          Schema as returned by Solr.
        """
        response = self.make_request("get", self.url)
        if response:
            return response.schema

    def list_fields(
        self,
        fields: list = None,
        includeDynamic: bool = False,
        showDefaults: bool = False,
    ) -> list:
        """Get a list of field definitions for a Solr Collection or core.

        Args:
          fields: A list of fields to filter by.
          includeDynamic: Include Solr dynamic fields in search.
          showDefaults: Show default Solr fields.

        Returns:
          list of fields as returned by Solr.
        """
        url = urljoin("%s/" % self.url, "fields")
        params = {}
        if fields:
            params["fl"] = ",".join(fields)
        params["includeDynamic"] = includeDynamic
        params["showDefaults"] = showDefaults
        response = self.make_request("get", url, params=params)
        if response:
            return response.fields

    def list_copy_fields(
        self, source_fl: Optional[list] = None, dest_fl: Optional[list] = None
    ) -> List[AttrDict]:
        """Return a list of copy fields from Solr.

        Args:
            source_fl: Source field to filter by.
            dest_fl: Destination field to filter by.

        Returns:
            list of copy fields as returned by Solr.
        """
        url = urljoin("%s/" % self.url, "copyfields")
        params = {}
        if source_fl:
            params["source.fl"] = ",".join(source_fl)
        if dest_fl:
            params["dest.fl"] = ",".join(dest_fl)
        response = self.make_request("get", url, params=params)
        if response:
            return response.copyFields

    def list_field_types(self, showDefaults: bool = True) -> List[AttrDict]:
        """List all field types in a Solr collection or core.

        Args:
            showDefaults: Show default fields

        Returns:
          list of copy fields as returned by Solr.
        """
        url = urljoin("%s/" % self.url, "fieldtypes")
        params = {}
        params["showDefaults"] = showDefaults
        response = self.make_request("get", url, params=params)
        if response:
            return response.fieldTypes
