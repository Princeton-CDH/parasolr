"""
Provides optional Django integration to automatically initialize a
:class:`parasolr.solr.SolrClient` with configurations from Django
settings.

Expected configuration format::

    SOLR_CONNECTIONS = {
        'default': {
            'URL': 'http://localhost:8983/solr/',
            'COLLECTION': 'mycore'
        }
    }

Collection can be omitted when connecting to a single-core Solr
instance.
"""

import logging
from typing import Any, Optional

from parasolr.django.util import requires_django
from parasolr.solr import client

try:
    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured
except ImportError:
    django = None


logger = logging.getLogger(__name__)


@requires_django
class SolrClient(client.SolrClient):
    """:class:`~parasolr.solr.client.SolrClient` subclass that
    automatically pulls configuration from Django settings.

    Args:
        *args: Positional arguments to be passed to :class:`parasolr.solr.client.SolrClient`.
        **kwargs: Keyword arguments to be passed to :class:`parasolr.solr.client.SolrClient`.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        solr_opts = getattr(settings, "SOLR_CONNECTIONS", None)
        # no solr connection section at all
        if not solr_opts:
            raise ImproperlyConfigured(
                "SolrClient requires SOLR_CONNECTIONS in settings"
            )

        default_solr = solr_opts.get("default", None)
        # no default config
        if not default_solr:
            raise ImproperlyConfigured(
                'No "default" section in SOLR_CONNECTIONS configuration'
            )

        url = default_solr.get("URL", None)
        # URL is required
        if not url:
            raise ImproperlyConfigured(
                "No URL in default SOLR_CONNECTIONS configuration"
            )

        collection = default_solr.get("COLLECTION", "")

        # use commit within if configured
        commit_within = default_solr.get("COMMITWITHIN", None)
        # passed-in value takes precedence
        if "commitWithin" not in kwargs and commit_within:
            kwargs["commitWithin"] = commit_within

        logger.info("Connecting to default Solr %s%s", url, collection)
        super().__init__(url, collection, *args, **kwargs)
