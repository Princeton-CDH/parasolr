"""
Provides optional Django integration to automatically initialize a
:class:`parasol.solr.SolrClient` with configurations from Django
settings.

Expected configuration format:

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
from typing import Any

try:
    import django
    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured
except ImportError:
    django = None

from parasol.solr import client


logger = logging.getLogger(__name__)


if django:

    class SolrClient(client.SolrClient):
        """:class:`SolrClient` subclass that automatically pulls configuration
        from django settings.

        Args:
            *args: Positional arguments to be passed to :class:`parasol.solr.client.SolrClient`.
            **kwargs: Keyword arguments to be passed to :class:`parasol.solr.client.SolrClient`.
        """

        def __init__(self, *args: Any, **kwargs: Any):
            solr_opts = getattr(settings, 'SOLR_CONNECTIONS', None)
            # no solr connection section at all
            if not solr_opts:
                raise ImproperlyConfigured('SolrClient requires SOLR_CONNECTIONS in settings')

            default_solr = solr_opts.get('default', None)
            # no default config
            if not default_solr:
                raise ImproperlyConfigured('No "default" section in SOLR_CONNECTIONS configuration')

            url = default_solr.get('URL', None)
            # URL is required
            if not url:
                raise ImproperlyConfigured('No URL in default SOLR_CONNECTIONS configuration')

            collection = default_solr.get('COLLECTION', '')
            logger.info('Connecting to default Solr %s%s', url, collection)
            super().__init__(url, collection, *args, **kwargs)
