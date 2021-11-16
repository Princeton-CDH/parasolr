from datetime import datetime

from parasolr.utils import solr_timestamp_to_datetime


def test_solr_timestamp_to_datetime():
    # with microseconds
    solr_dt = solr_timestamp_to_datetime("2018-07-02T21:08:46.428Z")
    assert solr_dt == datetime(2018, 7, 2, 21, 8, 46)
    # without
    solr_dt = solr_timestamp_to_datetime("2018-07-02T21:08:46Z")
    assert solr_dt == datetime(2018, 7, 2, 21, 8, 46)
