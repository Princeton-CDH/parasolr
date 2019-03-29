.. _CHANGELOG:

CHANGELOG
=========


0.2
---

* Subquent calls to SolrQuerySet.only() now *replaces* field limit options
  rather than adding to them.
* New SolrQuerySet method `raw_query_parameters`

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
