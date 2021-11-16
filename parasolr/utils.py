from datetime import datetime


def solr_timestamp_to_datetime(solr_time):
    """Convert Solr timestamp (isoformat that may or may not include
    microseconds) to :class:`datetime.datetime`"""
    # Solr stores date in isoformat; convert to datetime object
    # - microseconds only included when second is not exact; strip out if
    #    they are present
    if "." in solr_time:
        solr_time = "%sZ" % solr_time.split(".")[0]
    return datetime.strptime(solr_time, "%Y-%m-%dT%H:%M:%SZ")
