from unittest.mock import Mock, patch

import pytest
from attrdict import AttrDict

from parasolr import schema
from parasolr.solr import SolrClient


def test_solr_fields():
    """unit test for solr field descriptor"""

    # create a class with fields to test field descriptors
    class TestySolrFields:
        mystring = schema.SolrStringField()
        required_str = schema.SolrStringField(required=True)
        multival_str = schema.SolrStringField(multivalued=True)
        custom_field = schema.SolrField("text_en")
        last_modified = schema.SolrField("date", default="NOW")
        unstored = schema.SolrField("text_en", stored=False)

    # get on the field returns solr config info
    assert TestySolrFields.mystring == {
        "type": "string",
        "required": False,
        "multiValued": False,
        "stored": True,
    }
    assert TestySolrFields.required_str == {
        "type": "string",
        "required": True,
        "multiValued": False,
        "stored": True,
    }
    assert TestySolrFields.multival_str == {
        "type": "string",
        "required": False,
        "multiValued": True,
        "stored": True,
    }
    assert TestySolrFields.custom_field == {
        "type": "text_en",
        "required": False,
        "multiValued": False,
        "stored": True,
    }
    # with default specified
    assert TestySolrFields.last_modified == {
        "type": "date",
        "required": False,
        "multiValued": False,
        "default": "NOW",
        "stored": True,
    }
    # with stored false
    assert TestySolrFields.unstored == {
        "type": "text_en",
        "required": False,
        "multiValued": False,
        "stored": False,
    }

    # explicitly read-only
    with pytest.raises(AttributeError):
        TestySolrFields().mystring = "foo"


class TestAnalyzer(schema.SolrAnalyzer):
    """test analyzer for checking analyzer and field type logic"""

    tokenizer = "solr.StandardTokenizerFactory"
    filters = [
        {
            "class": "solr.StopFilterFactory",
            "ignoreCase": True,
            "words": "lang/stopwords_en.txt",
        },
        {"class": "solr.LowerCaseFilterFactory"},
    ]


def test_analyzer():
    analyzer_conf = TestAnalyzer.as_solr_config()
    assert analyzer_conf["tokenizer"]["class"] == TestAnalyzer.tokenizer
    assert analyzer_conf["filters"] == TestAnalyzer.filters


def test_solr_field_types():
    """unit test for solr field type descriptor and analyzer"""

    # create a class with fields to test field descriptors
    class TestSchema:
        # field type declaration
        text_en = schema.SolrFieldType("solr.TextField", analyzer=TestAnalyzer)

    # get on the field type returns solr config details
    field_config = TestSchema.text_en
    assert field_config["class"] == "solr.TextField"
    assert field_config["analyzer"] == TestAnalyzer.as_solr_config()

    # explicitly read-only
    with pytest.raises(AttributeError):
        TestSchema().text_en = "foo"


class TestSchema:
    def test_get_configuration__none(self):
        # error if no subclass defined
        with pytest.raises(Exception) as excinfo:
            schema.SolrSchema.get_configuration()
        assert "No Solr schema configuration found" in str(excinfo.value)

    def test_get_configuration__one(self):
        # define one subclass
        class SchemaOne(schema.SolrSchema):
            pass

        assert schema.SolrSchema.get_configuration() == SchemaOne

    def test_get_configuration__multiple(self):
        # define more than one subclass
        class SchemaOne(schema.SolrSchema):
            pass

        class SchemaTwo(schema.SolrSchema):
            pass

        with pytest.raises(Exception) as excinfo:
            schema.SolrSchema.get_configuration()
        assert "Currently only one Solr schema configuration is supported" in str(
            excinfo.value
        )

    def test_get_field_names(self):
        class LocalTestSchema(schema.SolrSchema):
            name = schema.SolrStringField(required=True)
            title = schema.SolrStringField()
            date = schema.SolrField("date")

        schemafields = LocalTestSchema.get_field_names()
        for field in ["name", "title", "date"]:
            assert field in schemafields

    def test_get_field_types(self):
        class TestAnalyzer(schema.SolrAnalyzer):
            pass

        class LocalTestSchema(schema.SolrSchema):
            text_en = schema.SolrFieldType("solr.TextField", analyzer=TestAnalyzer)
            text_sp = schema.SolrFieldType("solr.TextField", analyzer=TestAnalyzer)

        field_types = LocalTestSchema.get_field_types()
        for field_type in ["text_en", "text_sp"]:
            assert field_type in field_types

    def test_configure_fields(self):
        mocksolr = Mock()

        class LocalTestSchema(schema.SolrSchema):
            name = schema.SolrStringField(required=True)
            title = schema.SolrStringField()
            date = schema.SolrField("date")

        with patch.object(
            LocalTestSchema, "configure_copy_fields"
        ) as mock_config_cp_fields:

            # simulate only standard fields defined
            mocksolr.schema.list_fields.return_value = [
                AttrDict({"name": "id"}),
                AttrDict({"name": "_version_"}),
            ]

            result = LocalTestSchema.configure_fields(mocksolr)
            assert result.added == 3
            assert result.replaced == 0
            assert result.deleted == 0
            assert mock_config_cp_fields.call_count == 1

            # add field with field config options should be called for each
            for field in ["name", "title", "date"]:
                mocksolr.schema.add_field.assert_any_call(
                    name=field, **getattr(LocalTestSchema, field)
                )

            mocksolr.schema.replace_field.assert_not_called()
            mocksolr.schema.delete_field.assert_not_called()

            # simulate all standard fields defined and one extra
            mocksolr.reset_mock()
            mocksolr.schema.list_fields.return_value = [
                AttrDict({"name": "name"}),
                AttrDict({"name": "title"}),
                AttrDict({"name": "date"}),
                AttrDict({"name": "foobar"}),
            ]

            result = LocalTestSchema.configure_fields(mocksolr)
            assert result.added == 0
            assert result.replaced == 3
            assert result.deleted == 1
            mocksolr.schema.add_field.assert_not_called()
            # replace field with field config options should be called for each
            for field in ["name", "title", "date"]:
                mocksolr.schema.replace_field.assert_any_call(
                    name=field, **getattr(LocalTestSchema, field)
                )

            mocksolr.schema.delete_field.assert_called_with("foobar")

    def test_configure_copy_fields(self):
        mocksolr = Mock()

        class LocalTestSchema(schema.SolrSchema):
            #: copy fields, e.g. for facets or default search field ('text')
            copy_fields = {
                "author": ["text", "author_exact"],
                "collections": "collections_s",
                "title": ["title_nostem", "title_s"],
                "subtitle": "subtitle_s",
            }

        # simulate no copy fields
        mocksolr.schema.list_copy_fields.return_value = []
        LocalTestSchema.configure_copy_fields(mocksolr)
        # should be called once for each
        for source, dest in LocalTestSchema.copy_fields.items():
            mocksolr.schema.add_copy_field.assert_any_call(source, dest)
        # delete not called
        mocksolr.schema.delete_copy_field.assert_not_called()

        # simulate some to not be added, some to remove
        mocksolr.reset_mock()
        mocksolr.schema.list_copy_fields.return_value = [
            # valid source and destination in list
            AttrDict({"source": "author", "dest": "text"}),
            # valid source, destination not in list
            AttrDict({"source": "author", "dest": "foobar"}),
            # valid source & destination
            AttrDict({"source": "collections", "dest": "collections_s"}),
            # invalid source
            AttrDict({"source": "foo", "dest": "bar"}),
            # valid source, destination not == value
            AttrDict({"source": "subtitle", "dest": "baz"}),
        ]

        LocalTestSchema.configure_copy_fields(mocksolr)
        # should be called for title, subtitle, and second author dest
        assert mocksolr.schema.add_copy_field.call_count == 3

        # extra author copy dest should be removed
        mocksolr.schema.delete_copy_field.assert_any_call("author", "foobar")
        # extra source/dest should be removed
        mocksolr.schema.delete_copy_field.assert_any_call("foo", "bar")
        mocksolr.schema.delete_copy_field.assert_any_call("subtitle", "baz")
        assert mocksolr.schema.delete_copy_field.call_count == 3

    def test_configure_field_types(self):
        mocksolr = Mock()

        class TestAnalyzer(schema.SolrAnalyzer):
            pass

        class LocalTestSchema(schema.SolrSchema):
            text_en = schema.SolrFieldType("solr.TextField", analyzer=TestAnalyzer)

        # simulate no field types defined
        mocksolr.schema.list_field_types.return_value = []
        # current_field_types = {ftype['name']: ftype
        # for ftype in solr.schema.list_field_types()}
        # simulate only standard fields defined

        result = LocalTestSchema.configure_fieldtypes(mocksolr)
        assert result.added == 1
        assert result.updated == 0

        mocksolr.schema.add_field_type.assert_called_with(
            name="text_en", **LocalTestSchema.text_en
        )
        mocksolr.schema.replace_field_type.assert_not_called()

        # simulate field type already defined
        mocksolr.reset_mock()
        mocksolr.schema.list_field_types.return_value = [{"name": "text_en"}]
        result = LocalTestSchema.configure_fieldtypes(mocksolr)
        assert result.added == 0
        assert result.updated == 1
        mocksolr.schema.replace_field_type.assert_called_with(
            name="text_en", **LocalTestSchema.text_en
        )
        mocksolr.schema.add_field_type.assert_not_called()

        # no field types defined - should not error, do nothing
        assert not schema.SolrSchema.configure_fieldtypes(mocksolr)
