try:
    from parasolr.django.queryset import AliasedSolrQuerySet, SolrQuerySet
    from parasolr.django.solrclient import SolrClient
except ImportError:
    pass
