django-parasol
==============

**django-parasol** is a reusable `Django`_ application to simplify interacting
with `Apache Solr`_ by providing functionality to build a Solr schema and to index Django
models and other data as Solr documents, as well as management command
functionality for interacting with a Solr core.

.. _Django: https://www.djangoproject.com/
.. _Apache Solr: http://lucene.apache.org/solr/

Installation
------------

To install before an official pypa release::

   pip install git+https://github.com/Princeton-CDH/django-parasol@develop#egg=parasol


To use with Django:

    * Add `parasol` to **INSTALLED_APPS*
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

- recommmended: create and activate a Python 3.6 virtualenv::

   virtualenv parasol -p python3.6
   source parasol/bin/activate

- pip install the package with its dependencies::

   pip install -e .

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




