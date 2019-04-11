parasolr
==============

.. sphinx-start-marker-do-not-remove

**parasolr** is a lightweight python library for `Apache Solr`_ indexing,
searching and schema management with optional `Django`_ integration.
It includes a Solr client (`parasolr.solr.SolrClient`). When used with
Django, it provides management commands for updating your Solr schema
configuration and indexing content.

.. _Django: https://www.djangoproject.com/
.. _Apache Solr: http://lucene.apache.org/solr/

.. image:: https://travis-ci.org/Princeton-CDH/parasolr.svg?branch=master
   :target: https://travis-ci.org/Princeton-CDH/parasolr
   :alt: Build status

.. image:: https://codecov.io/gh/Princeton-CDH/parasolr/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/Princeton-CDH/parasolr
   :alt: Code coverage

.. image:: https://readthedocs.org/projects/parasolr/badge/?version=latest
  :target: https://parasolr.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

.. image:: https://api.codeclimate.com/v1/badges/73394d05decdf32f12f3/maintainability
   :target: https://codeclimate.com/github/Princeton-CDH/parasolr/maintainability
   :alt: Maintainability

.. image:: https://requires.io/github/Princeton-CDH/parasolr/requirements.svg?branch=master
     :target: https://requires.io/github/Princeton-CDH/parasolr/requirements/?branch=master
     :alt: Requirements Status

Currently tested against Python 3.5 and 3.6, Solr 6.6.5, and Django 1.11,
2.0, and 2.1, and without Django.


Installation
------------

Install released version from pypi::

   pip install parasolr

To install an unreleased version from GitHub::

   pip install git+https://github.com/Princeton-CDH/parasolr@develop#egg=parasolr

To use with Django:

* Add `parasolr` to **INSTALLED_APPS**
* Configure **SOLR_CONNECTIONS** in your django settings::

    SOLR_CONNECTIONS = {
        'default': {
        'URL': 'http://localhost:8983/solr/',
        'COLLECTION': 'name',
        # any configSet in SOLR_ROOT/server/solr/configsets
        'CONFIGSET': 'basic_configs' # optional, basic_configs is default
        }
    }

* Define a `SolrSchema` with fields and field types for your project.
* Run ``solr_schema`` manage command to configure your schema; it will
  prompt to create the Solr core if it does not exist.

.. Note::
   The `SolrSchema` must be imported somewhere for it to be
   found automatically.


Development instructions
------------------------

This git repository uses git flow branching conventions.

Initial setup and installation:

- *Recommmended*: create and activate a Python 3.6 virtualenv::

   virtualenv parasolr -p python3.6
   source parasolr/bin/activate

- Install the package with its dependencies as well as development
  dependencies::

   pip install -e .
   pip install -e '.[dev]''

Unit testing
------------

Unit tests are written with `pytest`_ but use some Django
test classes for compatibility with Django test suites. Running the tests
requires a minimal settings file for Django-required configurations.

.. _pytest: http:/docs.pytest.org

- Copy sample test settings and add a secret key::

   cp ci/testsettings.py.sample testsettings.py
   python -c "import uuid; print('\nSECRET_KEY = \'%s\'' % uuid.uuid4())" >> testsettings.py

- To run the test, either use the configured setup.py test command::

   python setup.py test

- Or install test requirements in and use pytest directly::

   pip install -e '.[test]'
   pytest




