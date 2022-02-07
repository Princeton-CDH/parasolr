default_app_config = "parasolr.apps.ParasolConfig"

__version_info__ = (0, 8, 2, None)

# Dot-connect all but the last. Last is dash-connected if not None.
__version__ = ".".join([str(i) for i in __version_info__[:-1]])
if __version_info__[-1] is not None:
    __version__ += "-%s" % (__version_info__[-1],)
