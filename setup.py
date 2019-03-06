import os
import sys
from setuptools import find_packages, setup
from parasolr import __version__

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

REQUIREMENTS = ['requests', 'attrdict', 'progressbar2']
# NOTE: progressbar only needed for django index script; make optional?
TEST_REQUIREMENTS = ['pytest', 'pytest-cov']
DEV_REQUIREMENTS = ['sphinx', 'sphinxcontrib-napoleon',
                    'sphinx-autodoc-typehints']
# django integration is optional
DJANGO_REQUIREMENTS = ['django>=1.11', 'pytest-django']

setup(
    name='parasolr',
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    license='Apache License, Version 2.0',
    description='Lightweight python library for Solr indexing, searching' +
        ' and schema management with optional Django integration.',
    long_description=README,
    url='https://github.com/Princeton-CDH/parasolr',
    install_requires=REQUIREMENTS,
    setup_requires=['pytest-runner'],
    tests_require=TEST_REQUIREMENTS,
    extras_require={
        'test': TEST_REQUIREMENTS,
        'django': DJANGO_REQUIREMENTS,
        'dev': TEST_REQUIREMENTS + DEV_REQUIREMENTS + DJANGO_REQUIREMENTS,
    },
    author='The Center for Digital Humanities at Princeton',
    author_email='cdhdevteam@princeton.edu',
    classifiers=[
        'Environment :: Web Environment',
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Database',
    ],
    entry_points={
        'pytest11': [
            'parasolr = parasolr.pytest_plugin',
        ]
    },
)
