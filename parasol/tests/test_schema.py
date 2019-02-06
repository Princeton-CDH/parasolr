import pytest

from parasol import schema


def test_solr_fields():
    '''unit test for solr field descriptor'''

    # create a class with fields to test field descriptors
    class TestySolrFields:
        mystring = schema.SolrStringField()
        required_str = schema.SolrStringField(required=True)
        multival_str = schema.SolrStringField(multivalued=True)
        custom_field = schema.SolrField('text_en')

    # get on the field returns solr config info
    assert TestySolrFields.mystring ==  \
        {'type': 'string', 'required': False, 'multiValued': False}
    assert TestySolrFields.required_str ==  \
        {'type': 'string', 'required': True, 'multiValued': False}
    assert TestySolrFields.multival_str ==  \
        {'type': 'string', 'required': False, 'multiValued': True}
    assert TestySolrFields.custom_field ==  \
        {'type': 'text_en', 'required': False, 'multiValued': False}

    # explicitly read-only
    with pytest.raises(AttributeError):
        TestySolrFields().mystring = 'foo'

class TestAnalyzer(schema.SolrAnalyzer):
    ''' test analyzer for checking analyzer and field type logic'''
    tokenizer = 'solr.StandardTokenizerFactory'
    filters = [
        {"class": "solr.StopFilterFactory", "ignoreCase": True,
         "words": "lang/stopwords_en.txt"},
        {"class": "solr.LowerCaseFilterFactory"},
    ]


def test_analyzer():
    analyzer_conf = TestAnalyzer.as_solr_config()
    assert analyzer_conf['tokenizer']['class'] == TestAnalyzer.tokenizer
    assert analyzer_conf['filters'] == TestAnalyzer.filters


def test_solr_field_types():
    '''unit test for solr field type descriptor and analyzer'''

    # create a class with fields to test field descriptors
    class TestSchema:
        # field type declaration
        text_en = schema.SolrFieldType('solr.TextField',
                                       analyzer=TestAnalyzer)

    # get on the field type returns solr config details
    field_config = TestSchema.text_en
    assert field_config['class'] == 'solr.TextField'
    assert field_config['analyzer'] == TestAnalyzer.as_solr_config()

    # explicitly read-only
    with pytest.raises(AttributeError):
        TestSchema().text_en = 'foo'
