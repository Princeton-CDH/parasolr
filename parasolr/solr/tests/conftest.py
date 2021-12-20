import sys
import uuid

import pytest

from parasolr.solr.base import ClientBase, CoreExists, ImproperConfiguration
from parasolr.solr.client import SolrClient

# - Handling for test settings integrated into CI flow.
try:
    from django import settings
except ImportError:
    # append top level working directory to path to add  testsettings
    sys.path.append(".")
    try:
        import testsettings as settings
    except ImportError:
        raise ImportError("No Django or parasolr test settings module found.")

try:
    TEST_SOLR_CONNECTION = settings.SOLR_CONNECTIONS["default"]["TEST"]
# reraise whether or not the key is missing for 'test' OR the entire setting
# is missing.
except (AttributeError, KeyError) as err:
    raise err.__class__(
        'Check that a SOLR_CONNECTIONS block with a "TEST" entry ' "is defined."
    )


# Any fields listed here will be cleaned up after every test,
# as they persist--even across a core being unloaded.
# If you add fields and don't update this list, unexpected behavior
# will almost certainly result.
TEST_FIELDS = ["A", "B", "C", "D"]

# Copy fields used in tests, with tuples of (source, dest)
TEST_COPY_FIELDS = [("A", "B"), ("C", "D")]

# Field types that need to be cleared after each run
TEST_FIELD_TYPES = ["test_A", "test_B"]


@pytest.fixture
def test_client(request):
    """Creates and returns a Solr core using TEST_SETTINGS, and then removes
    it on teardown, as well as all TEST_* fields.

    If a test field is listed here, it will NOT be automatically cleaned up.
    """

    solr_url = TEST_SOLR_CONNECTION.get("URL", None)
    collection = TEST_SOLR_CONNECTION.get("COLLECTION", None)
    commitWithin = TEST_SOLR_CONNECTION.get("COMMITWITHIN", None)

    if not solr_url or not collection:
        raise ImproperConfiguration(
            "Test client requires URL and COLLECTION in SOLR_CONNECTIONS."
        )

    client = SolrClient(solr_url, collection, commitWithin=commitWithin)

    response = client.core_admin.status(core=collection)
    if response.status.parasolr_test:
        raise CoreExists('Test core "parasolr_test" exists, aborting!')
    client.core_admin.create(collection, configSet=TEST_SOLR_CONNECTION["CONFIGSET"])

    def clean_up():
        for field in TEST_FIELDS:
            client.schema.delete_field(field)
        for source, dest in TEST_COPY_FIELDS:
            client.schema.delete_copy_field(source=source, dest=dest)
        for ftype in TEST_FIELD_TYPES:
            client.schema.delete_field_type(name=ftype)
        client.core_admin.unload(
            collection, deleteInstanceDir=True, deleteIndex=True, deleteDataDir=True
        )

    request.addfinalizer(clean_up)
    return client


@pytest.fixture
def core_test_client(request):
    """Create a core name and pass an unconfigured client for it,
    along with name to fixture.

    Unconditionally deletes the core named, so that any CoreAdmin API tests
    are always cleaned up on teardown.
    """
    solr_url = TEST_SOLR_CONNECTION.get("URL", None)
    commitWithin = TEST_SOLR_CONNECTION.get("COMMITWITHIN", None)

    if not solr_url:
        raise ImproperConfiguration(
            "Core admin test client requires URL setting in SOLR_CONNECTIONS."
        )

    core_name = str(uuid.uuid4())

    client = SolrClient(solr_url, core_name, commitWithin=commitWithin)

    def clean_up():

        client.core_admin.unload(
            core_name, deleteInstanceDir=True, deleteIndex=True, deleteDataDir=True
        )

    request.addfinalizer(clean_up)
    return (client, core_name)
