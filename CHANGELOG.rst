.. _CHANGELOG:

CHANGELOG
=========

0.3
---

* Add support for ``__in`` queries to ``filter`` method of ``SolrQuerySet``
* Add support for ``__exists`` queries to `Filter to determine if a field is empty or missing.
* Add ``facet_field`` method to ``SolrQuerySet`` to configure facet fields individual.
* Add support for `tag` and `exclude` to ``filter`` and ``facet_field`` methods of ``SolrQuerySet``.

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
