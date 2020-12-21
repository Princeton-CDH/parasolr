Getting Started
---------------

To use ``parasolr`` you need a `Solr installation <https://lucene.apache.org/solr/guide/6_6/installing-solr.html>`_ that you can connect to. Once you have Solr set up,
use ``solr start`` to make sure it's running, and then create a new core: ``solr create -c core_name``.

To interact with solr, use the :class:`~parasolr.solr.client.SolrClient` included in parasolr.
It should be initialized with the URL for your Solr installation and the name of the core you want to query::

    from parasolr.solr.client import SolrClient

    solr_url = "http://localhost:8983/solr"
    solr_core = "core_name"
    solr = SolrClient(solr_url, solr_core)

Now you can index some data. The index method takes a list of
dictionaries; note that any content you include must be JSON-serializable.
For example, to index data from a CSV file::

    solr.update.index([{
        "id": row["id"],
        "name": row["name"],
        "tags": row['tags'].split('|')
        # etc ...
    } for row in csv])

To query the data you've indexed, initialize a :class:`~parasolr.query.queryset.SolrQuerySet`, passing it
the solr client you used before::

    from parasolr.query import SolrQuerySet

    queryset = SolrQuerySet(solr)
    queryset = queryset.search('search string').order_by('name')
    results = queryset.get_results(rows=20)

``results`` contains a list of dictionaries that you're can manipulate or display as needed.

To remove records from your solr core, you can delete based on a query.
For example, to delete all indexed items::

    solr.update.delete_by_query('*:*')
