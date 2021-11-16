"""pytest plugin to disconnect index signal handlers at the beginning
of the testing session. enable by adding:
`addopts = -p parasolr.django.disconnect_indexing`
to your pytest.ini."""


def pytest_sessionstart(session):
    from parasolr.django.signals import IndexableSignalHandler

    IndexableSignalHandler.disconnect()
