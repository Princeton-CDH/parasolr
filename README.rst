parasol
==============

.. sphinx-start-marker-do-not-remove

**parasol** is a lightweight python library for `Apache Solr`_ indexing,
searching and schema management with optional `Django`_ integration.
It includes a Solr client (`parasol.solr.SolrClient`). When used with
Django, it provides management commands for updating your Solr schema
configuration and indexing content.

.. _Django: https://www.djangoproject.com/
.. _Apache Solr: http://lucene.apache.org/solr/

Installation
------------

To install before an official pypi release::

   pip install git+https://github.com/Princeton-CDH/parasol@develop#egg=parasol

To use with Django:

    * Add `parasol` to **INSTALLED_APPS**
    * Configure **SOLR_CONNECTIONS** in your django settings::

    SOLR_CONNECTIONS = {
        'default': {
        'URL': 'http://localhost:8983/solr/',
        'COLLECTION': 'name',
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

   virtualenv parasol -p python3.6
   source parasol/bin/activate

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




