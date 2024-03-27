.. _CHANGELOG:

CHANGELOG
=========

0.9.2
-----
* bugfix: ``AliasedSolrQuerySet`` now supports aliasing for keyword arguments
 when calling the `search` method

0.9.1
----

* Solr 9 compatible; now tested against Solr 9.2 and 8.6
* Dropped support for python 3.7; now tested against python 3.9-3.11
* Now tested against Django 4.0 and 3.2

0.9
---

* ``SolrQuerySet`` now supports Solr grouping via new `group`
  method and `GroupedResponse`
* New class method `prep_index_chunk` on ``Indexable`` class, to support
  prefetching related objects when iterating over Django querysets for indexing
* Include django view mixins in sphinx documentation  
* Dropped support for python 3.6; added python 3.9
* Dropped support for Django 2.2; added Django 3.2
* No longer tested against Solr 6.6

0.8.2
-----

* When subclassing ``SolrQuerySet``, result documents can now be customized by extending ``get_result_document``

0.8.1
-----
* Exclude proxy models when collecting indexable subclasses

0.8
---
* Pytest fixture ``mock_solr_queryset`` now takes optional argument for extra methods to include in fluent interface
* ``SolrQuerySet`` now supports highlighting on multiple fields via ``highlight`` method, with per-field highlighting options.
* ``AliasedSolrQuerySet`` now correctly aliases fieldnames in highlighting results.
* Adopted black & isort python style and configured pre-commit hook

0.7
---

* Dropped support for Python 3.5
* Now tested against Python 3.6, 3.8, Django 2.2—3.1, Solr 6 and Solr 8
* Continuous integration migrated from Travis-CI to GitHub Actions
* bugfix: in some cases, index script was wrongly detecting ModelIndexable
  subclasses as abstract and excluding them; this has been corrected
* ModelIndexable now extends ``django.db.models.Model``; existing code
  MUST be updated to avoid double-extending Model
* Default index data has been updated to use a dynamic field ``item_type_s`` instead of ``item_type`` so that basic setup does not require customizing the solr schema.
* ``ModelIndexable.get_related_model`` now supports ForeignKey relationships and django-taggit ``TaggableManager`` when identifying depencies for binding signal handlers

0.6.1
-----

* bugfix: fix regression in SolrQuerySet `get_stats` in 0.6

0.6
---

* Solr client now escalates 404 errors instead of logging with no exception
* Schema field declarations now support the ``stored`` option
* Schema field type declarations now pass through arbitrary options
* New method ``total_to_index`` on ``parasolr.indexing.Indexable`` to better
  support indexing content that is returned as a generator
* Access to expanded results now available on QueryResponse and SolrQuerySet
* SolrQuerySet no longer wraps return results from ``get_stats`` and ``get_facets`` with QueryResponse
* New last-modified view mixin for use with Django views ``parasolr.django.views.SolrLastModifiedMixin``
* New pytest fixture ``mock_solr_queryset`` to generate a Mock SolrQuerySet that simulates the SolrQuerySet fluent interface


0.5.4
-----

* Only enable pytest plugin when parasolr is in Django installed apps
  and a Solr connection is configured

0.5.3
---

* Support default option adding fields to solr schema
* Add utility method to convert Solr timestamp to python datetime

0.5.2
-----

* bugfix: correct queryset highlighting so it actually works
* Revise pytest plugin code to work on non-django projects

0.5.1
-----

* bugfix: SolrQuerySet improved handling for Solr errors

0.5
---

- Support for on-demand indexing for Django models based on signals;
  see ``parasolr.django.signals``; adds a Django-specific indexable class
  ``parasolr.django.indexing.ModelIndexable``
- pytest plugin to disconnect django signal handlers
- Django pytest fixture for an empty solr
- Adds an EmptySolrQuerySet class, as a simpler way to check for empty results


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
