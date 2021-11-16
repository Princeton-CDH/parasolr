import logging

try:
    import django
except ImportError:
    django = None


logger = logging.getLogger(__name__)


def requires_django(cls):
    """Decorator for classes and methods that require Django.
    If Django is not available, warns and raises an import error.
    Otherwise, returns the wrapped object as-is (unwrapped).
    """
    if not django:
        logger.warning("Django is required for %s" % cls)
        raise ImportError
    return cls
