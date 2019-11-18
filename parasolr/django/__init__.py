try:
    from parasolr.django.solrclient import SolrClient
    from parasolr.django.queryset import SolrQuerySet, AliasedSolrQuerySet
except ImportError:
    pass
