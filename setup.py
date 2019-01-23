import os
import sys
from setuptools import find_packages, setup
from parasol import __version__

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

REQUIREMENTS = ['django>=1.8', 'SolrClient @ git+https://github.com/rlskoeser/SolrClient.git@schema-field-type-support']
TEST_REQUIREMENTS = ['pytest', 'pytest-django', 'pytest-cov']
if sys.version_info < (3, 0):
    TEST_REQUIREMENTS.append('mock')

setup(
    name='parasol',
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    license='Apache License, Version 2.0',
    description='Django application for Solr schema generation and indexing of models.',
    long_description=README,
    url='https://github.com/Princeton-CDH/django-parasol',
    install_requires=REQUIREMENTS,
    setup_requires=['pytest-runner'],
    tests_require=TEST_REQUIREMENTS,
    extras_require={
        'test': TEST_REQUIREMENTS,
    },
    author='CDH @ Princeton',
    author_email='digitalhumanities@princeton.edu',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Database',
    ]
)