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


* .. image:: https://badge.fury.io/py/parasolr.svg
   :target: https://badge.fury.io/py/parasolr
   :alt: PyPI version

  .. image:: https://img.shields.io/pypi/pyversions/parasolr.svg
   :alt: PyPI - Python Version

  .. image:: https://img.shields.io/pypi/djversions/parasolr.svg
   :alt: PyPI - Django Version

  .. image:: https://img.shields.io/pypi/l/parasolr.svg?color=blue
   :alt: PyPI - License

* .. image:: https://travis-ci.org/Princeton-CDH/parasolr.svg?branch=main
   :target: https://travis-ci.org/Princeton-CDH/parasolr
   :alt: Build status

  .. image:: https://codecov.io/gh/Princeton-CDH/parasolr/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/Princeton-CDH/parasolr
   :alt: Code coverage

  .. image:: https://readthedocs.org/projects/parasolr/badge/?version=latest
   :target: https://parasolr.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

  .. image:: https://www.codefactor.io/repository/github/princeton-cdh/parasolr/badge
   :target: https://www.codefactor.io/repository/github/princeton-cdh/parasolr
   :alt: CodeFactor

  .. image:: https://api.codeclimate.com/v1/badges/73394d05decdf32f12f3/maintainability
   :target: https://codeclimate.com/github/Princeton-CDH/parasolr/maintainability
   :alt: Maintainability

  .. image:: https://requires.io/github/Princeton-CDH/parasolr/requirements.svg?branch=main
    :target: https://requires.io/github/Princeton-CDH/parasolr/requirements/?branch=main
    :alt: Requirements Status

  .. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: code style: Black

  .. image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
    :target: https://pycqa.github.io/isort/

Currently tested against Python 3.6 and 3.8, Solr 6.6.5 and 8.6.2, and Django 2.2-3.1 and without Django.


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
        # Any configSet in SOLR_ROOT/server/solr/configsets.
        #   The default configset name is "_default" as of Solr 7.
        #   For Solr 6, "basic_configs" is the default.
        'CONFIGSET': '_default'
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

   python3 -m venv parasolr
   source parasolr/bin/activate

- Install the package with its dependencies as well as development
  dependencies::

   pip install -e .
   pip install -e '.[dev]'

Install pre-commit hooks
~~~~~~~~~~~~~~~~~~~~~~~~

Install configured pre-commit hooks (currently `black <https://github.com/psf/black>`_ and `isort <https://pycqa.github.io/isort/>`_):

    pre-commit install

Styling was instituted in version 0.8; as a result, ``git blame`` may not reflect the true author of a given line. In order to see a more accurate ``git blame`` execute the following command:

    git blame <FILE> --ignore-revs-file .git-blame-ignore-revs

Or configure your git to always ignore the black revision commit:

    git config blame.ignoreRevsFile .git-blame-ignore-revs


Unit testing
------------

Unit tests are written with `pytest`_ but use some Django
test classes for compatibility with Django test suites. Running the tests
requires a minimal settings file for Django-required configurations.

.. _pytest: http:/docs.pytest.org

- Copy sample test settings and add a secret key::

   cp ci/testsettings.py testsettings.py
   python -c "import uuid; print('\nSECRET_KEY = \'%s\'' % uuid.uuid4())" >> testsettings.py

- By default, parasolr expects Solr 8. If running tests with an earlier
  version of Solr, either explicitly change **MAJOR_SOLR_VERSION** in your
  local **testsettings.py** or set the environment variable::

   export SOLR_VERSION=x.x.x

- To run the test, either use the configured setup.py test command::

   python setup.py test

- Or install test requirements in and use pytest directly::

   pip install -e '.[test]'
   pytest


License
-------

**parasolr** is distributed under the Apache 2.0 License.

©2019 Trustees of Princeton University.  Permission granted via
Princeton Docket #20-3619 for distribution online under a standard Open Source
license.  Ownership rights transferred to Rebecca Koeser provided software
is distributed online via open source.


