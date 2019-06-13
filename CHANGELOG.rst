.. _CHANGELOG:

CHANGELOG
=========

0.4
---

* ``parasolr.query.SolrQuery`` additional support for stats:

  * New method ``stats`` to enable stats for a set of field names.
  * New method ``get_stats`` to return the entire stats reponse.


0.3
---

* ``parasolr.query.SolrQuerySet`` additional support for faceting:

  * New method ``facet_field`` for more fine-grained facet feature
    control for a single facet field
  * New method ``facet_range`` for enabling range faceting
  * Supports tag and exclusion logic via ``tag`` option on
    ``facet_field`` method and ``exclude`` option on ``filter``
  * ``get_facets`` now returns the entire facet response, including
    facet fields, range facets, etc.

* ``SolrQuerySet.filter()`` method now supports the following advanced lookups:

  * **in**: filter on a list of values
  * **exists**: filter on empty or not-empty
  * **range**: filter on a numeric range

* New method ``SolrQuerySet.also()`` that functions just like ``only()``
  except it adds instead of replacing field limit options.
* New ``parasolr.query.AliasedSolrQuerySet`` supports
  aliasing Solr fields to local names for use across all queryset methods
  and return values
* ``parasolr.indexing.Indexable`` now provides ``items_to_index()`` method
  to support customizing retrieving items for indexing with ``index``
  manage command.


0.2
---

* Subquent calls to ``SolrQuerySet.only()`` now *replaces* field limit options
  rather than adding to them.
* New SolrQuerySet method ``raw_query_parameters``
* SolrQuerySet now has support for faceting via ``facet`` method to configure
  facets on the request and ``get_facets`` to retrieve them from the response.
* Update ``ping`` method of ``parasolr.solr.admin.CoreAdmin`` so that
  a 404 response is not logged as an error.
* Refactor ``parsolr.solr`` tests into submodules

0.1.1
-----

* Fix travis-ci build for code coverage reporting.

0.1
---

Lightweight python library for Solr indexing, searching and schema
management with optional Django integration.

* Minimal Python Solr API client
* Logic for updating and managing Solr schema
* Indexable mixin for Django models
* QuerySet for querying Solr in an object-oriented fashion similar to
  Django QuerySet
* Django Solr client with configuration from Django settings
* Django manage command to configure Solr schema
* Django manage command to index subclasses of Indexable
* `pytest` plugin for unit testing against a test Solr instance in Django
* Basic Sphinx documentation
