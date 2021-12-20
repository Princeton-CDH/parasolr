"""
Provides :class:`~parasolr.query.SolrQuerySet` subclasses that
will automatically use :class:`~parasolr.django.SolrClient` if
no solr client is passed on.
"""

import logging
from typing import Optional

from parasolr import query
from parasolr.django.util import requires_django

# SolrClient needed for type annotation when testing without django
from parasolr.solr.client import SolrClient

try:
    from parasolr.django.solrclient import SolrClient

    django = True
except ImportError:
    django = None


logger = logging.getLogger(__name__)


@requires_django
class SolrQuerySet(query.SolrQuerySet):
    """:class:`~parasolr.query.SolrQuerySet` subclass that
    will automatically use :class:`~parasolr.django.SolrClient` if
    no solr client is passed on.

    Args:
        Optional :class:`parasolr.solr.client.SolrClient`
    """

    def __init__(self, solr: Optional[SolrClient] = None):
        # use passed-in solr client if there is one;
        # otherwise, initialize a django solr client
        super().__init__(solr or SolrClient())


@requires_django
class AliasedSolrQuerySet(SolrQuerySet, query.AliasedSolrQuerySet):
    """Combination of :class:`SolrQuerySet` and
    :class:`~parasolr.query.alias_queryset.AliasedSolrQuerySet`"""
