try:
    import django
except ImportError:
    django = None

from parasol.solr.client import SolrClient

if django:
    from parasol.solr.client import DjangoSolrClient
