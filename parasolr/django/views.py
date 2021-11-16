import calendar
import logging

from django.utils.cache import get_conditional_response
from django.views.generic.base import View

from parasolr.django import SolrQuerySet
from parasolr.solr import SolrClientException
from parasolr.utils import solr_timestamp_to_datetime

logger = logging.getLogger(__name__)


class SolrLastModifiedMixin(View):
    """View mixin to add last modified headers based on Solr.
    By default, searches entire solr collection and returns the most
    recent last modified value (assumes **last_modified** field).
    To filter for items specific to your view, either
    set :attr:`solr_lastmodified_filters` or
    implement :meth:`get_solr_lastmodified_filters`.
    """

    #: solr query filter for getting last modified date
    solr_lastmodified_filters = {}  # by default, find all

    def get_solr_lastmodified_filters(self):
        """Get filters for last modified Solr query. By default returns
        :attr:`solr_lastmodified_filters`."""
        return self.solr_lastmodified_filters

    def last_modified(self):
        """Return last modified :class:`datetime.datetime` from the
        specified Solr query"""
        filter_qs = self.get_solr_lastmodified_filters()
        sqs = (
            SolrQuerySet()
            .filter(**filter_qs)
            .order_by("-last_modified")
            .only("last_modified")
        )

        try:
            # Solr stores date in isoformat; convert to datetime
            return solr_timestamp_to_datetime(sqs[0]["last_modified"])
            # skip extra call to Solr to check count and just grab the first
            # item if it exists
        except (IndexError, KeyError, SolrClientException) as err:
            # if a syntax or other solr error happens, no date to return
            # report the error, but don't fail since the view may still
            # be able to render normally
            logger.error("Failed to retrieve last modified: %s" % err)
            # TODO: if possible, report view / args / url that triggering
            # the error

    def dispatch(self, request, *args, **kwargs):
        """Wrap the dispatch method to add a last modified header if
        one is available, then return a conditional response."""

        # NOTE: this doesn't actually skip view processing,
        # but without it we could return a not modified for a non-200 response
        response = super(SolrLastModifiedMixin, self).dispatch(request, *args, **kwargs)

        last_modified = self.last_modified()
        if last_modified:
            # remove microseconds so that comparison will pass,
            # since microseconds are not included in the last-modified header
            last_modified = last_modified.replace(microsecond=0)
            response["Last-Modified"] = last_modified.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )
            # convert the same way django does so that they will
            # compare correctly
            last_modified = calendar.timegm(last_modified.utctimetuple())

        return get_conditional_response(
            request, last_modified=last_modified, response=response
        )
