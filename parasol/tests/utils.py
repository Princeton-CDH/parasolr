import pytest

try:
    import django
except ImportError:
    django = None

skipif_no_django = pytest.mark.skipif(django is None,
                                      reason="requires Django")

skipif_django = pytest.mark.skipif(django,
                                   reason="requires no Django")
