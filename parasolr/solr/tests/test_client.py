import time
from collections import OrderedDict

import requests
from attrdict import AttrDict

from parasolr import __version__ as parasolr_ver
from parasolr.solr.admin import CoreAdmin
from parasolr.solr.client import ParasolrDict, QueryResponse, SolrClient
from parasolr.solr.schema import Schema
from parasolr.solr.update import Update

# NOTE: Field and field-type names must be registered and cleaned
# up in conftest.py
# Otherwise, they will be retained between test iterations and break results.


class TestParasolrDict:
    def test_as_dict(self):
        para_dict = ParasolrDict(
            {"a": 1, "b": ParasolrDict({"c": [1, 2, 3], "d": ParasolrDict({"z": 1})})}
        )
        as_dict = para_dict.as_dict()
        # no longer an attrdict
        assert not isinstance(as_dict, AttrDict)
        assert isinstance(as_dict, dict)
        # should be formatted so as to have preserved old arrangement
        assert as_dict == para_dict
        # subdictionaries should be dicts but not AttrDict subclasses
        assert not isinstance(as_dict["b"], AttrDict)
        assert isinstance(as_dict["b"], dict)
        assert not isinstance(as_dict["b"]["d"], AttrDict)
        assert isinstance(as_dict["b"]["d"], dict)
        # other structures should be untouched
        assert isinstance(as_dict["b"]["c"], list)

    def test_repr(self):
        data = {
            "a": 1,
        }
        para_dict = ParasolrDict(data)
        assert repr(para_dict) == "ParasolrDict(%s)" % repr(data)


class TestQueryResponse:
    def test_init(self):

        response = AttrDict(
            {
                "responseHeader": {"params": {"foo": "bar"}},
                "response": {
                    "numFound": 2,
                    "start": 0,
                    "docs": [
                        {"A": 5},
                        {"A": 2},
                        {"A": 3},
                    ],
                },
                "facet_counts": {
                    "facet_fields": {"A": ["5", 1, "2", 1, "3", 1]},
                    "facet_ranges": {"A": {"counts": ["1", 1, "2", 2, "7", 1]}},
                },
                "stats": {
                    "stats_fields": {
                        "account_start_i": {
                            "min": 1919.0,
                            "max": 2018.0,
                        }
                    }
                },
            }
        )
        qr = QueryResponse(response)
        assert qr.params == response.responseHeader.params
        assert qr.start == response.response.start
        assert qr.docs == response.response.docs
        assert qr.numFound == response.response.numFound
        assert qr.stats == response.stats
        assert isinstance(qr.facet_counts["facet_fields"]["A"], OrderedDict)
        assert isinstance(qr.facet_counts["facet_ranges"]["A"]["counts"], OrderedDict)
        assert qr.facet_counts["facet_fields"]["A"]["5"] == 1
        assert qr.facet_counts["facet_ranges"]["A"]["counts"]["2"] == 2
        assert qr.highlighting == {}


class TestSolrClient:
    def test_solr_client_init(self):
        solr_url = "http://localhost:8983/solr"
        collection = "testcoll"
        client = SolrClient(solr_url, collection)
        # check that args are respected
        assert client.solr_url == "http://localhost:8983/solr"
        assert client.collection == "testcoll"
        assert client.schema_handler == "schema"
        assert client.select_handler == "select"
        assert client.update_handler == "update"

        # check that api objects are set on the object as expected
        assert isinstance(client.schema, Schema)
        assert isinstance(client.update, Update)
        assert isinstance(client.core_admin, CoreAdmin)

        # test that sessions is a Session object
        assert isinstance(client.session, requests.Session)

        # test that session headers include the version name
        assert client.session.headers[
            "User-Agent"
        ] == "parasolr/%s (python-requests/%s)" % (parasolr_ver, requests.__version__)

    def test_query(self, test_client):
        # query of empty core produces the expected results
        # of no docs and no items
        response = test_client.query(q="*:*")
        assert response.numFound == 0
        assert response.start == 0
        assert not response.docs
        assert response.params["q"] == "*:*"
        assert response.params["wt"] == "json"
        # add a field and index some documents
        test_client.schema.add_field(name="A", type="string")
        test_client.schema.add_field(name="B", type="int")
        test_client.update.index(
            [
                {"A": "foo", "B": 5, "id": 1},
                {"A": "bar", "B": 20, "id": 2},
                {"A": "baz", "B": 25, "id": 3},
                {"A": "baz", "B": 30, "id": 4},
            ]
        )
        time.sleep(1)
        # get back two
        response = test_client.query(q="A:(bar OR baz)")
        assert response.numFound == 3
        # not paginated so should be starting at 0
        assert response.start == 0
        # should be the two expected documents
        # FIXME: these lines have no effect
        {"A": "bar", "B": 20, "id": 2}
        {"A": "baz", "B": 25, "id": 3} in response.docs
        {"A": "baz", "B": 30, "id": 4} in response.docs

        # test faceting in response
        response = test_client.query(
            q="*:*",
            facet="on",
            **{
                "facet.field": "A",
                "facet.range": "B",
                "f.B.facet.range.start": 1,
                "f.B.facet.range.end": 25,
                "f.B.facet.range.gap": 10,
            }
        )
        assert response.facet_counts
        assert response.facet_counts.facet_fields
        # must access using dict notation to get the OrderedDict as presented
        assert isinstance(response.facet_counts.facet_fields["A"], OrderedDict)
        assert response.facet_counts.facet_fields.A["bar"] == 1
        assert response.facet_counts.facet_fields.A["baz"] == 2
        assert isinstance(
            response.facet_counts.facet_ranges["B"]["counts"], OrderedDict
        )
        # check that the gaps are generated as expected
        assert response.facet_counts.facet_ranges["B"]["counts"]["1"] == 1
        assert response.facet_counts.facet_ranges["B"]["counts"]["11"] == 1

        # test wrap = False
        response = test_client.query(q="*:*", wrap=False)
        assert not isinstance(response, QueryResponse)
