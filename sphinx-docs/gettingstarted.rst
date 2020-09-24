Getting Started
---------------

To use ``parasolr`` you'll need to first make sure that solr is running 
(``solr start``), and create a solr core with the command 
``solr create_core -c core_name``.

To interact with solr, you'll need to first create a ``SolrClient`` instance::

    from parasolr.solr.client import SolrClient
    solr_url = "http://localhost:8983/solr"
    solr_core = "core_name"
    solr = SolrClient(solr_url, solr_core)

You can then ingest and index your data from a CSV. Remember, a unique
identifier is required::

    solr.update.index([{ 
        "id": row["id"],
        "etc": row["etc"], 
        # ...
    } for row in csv])

And then query the data::

    queryset = SolrQuerySet(solr)
    queryset = queryset.search(solr_query).order_by('some_var')
    results = queryset.get_results(rows=20)

``results`` now contains a list of dictionaries that you're welcome to query and
manipulate as needed.

To reset records within the solr core, you can delete all indexed items::

    solr.update.delete_by_query('*:*')
