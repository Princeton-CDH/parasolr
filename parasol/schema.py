from django.settings import settings

from SolrClient import SolrClient


def get_solr_connection():
    '''Initialize a Solr connection using project settings'''
    # TODO: error handling on config not present?
    solr_config = settings.SOLR_CONNECTIONS['default']
    solr = SolrClient(solr_config['URL'])
    # NOTE: may want to extend SolrClient to set a default collection
    solr_collection = solr_config['COLLECTION']
    return solr, solr_collection
