from parasolr.solr.tests.conftest import TEST_SOLR_CONNECTION

# NOTE: Field and field-type names must be registered and cleaned
# up in conftest.py
# Otherwise, they will be retained between test iterations and break results.


class TestSchema:

    def test_add_field(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert 'A' in names
        assert fields[names.index('A')].type == 'string'

    def test_delete_field(self, test_client):
        # add field and assert it exists
        test_client.schema.add_field(name='A', type='string')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert 'A' in names
        # delete it should not be there
        test_client.schema.delete_field(name='A')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert 'A' not in names

    def test_replace_fields(self, test_client):

        test_client.schema.add_field(name='A', type='string')
        test_client.schema.replace_field(name='A', type='pint')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert fields[names.index('A')].type == 'pint'


    def test_list_fields(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        test_client.schema.add_field(name='B', type='pint')
        fields = test_client.schema.list_fields()
        names = [f.name for f in fields]
        assert fields[names.index('A')].type == 'string'
        assert fields[names.index('B')].type == 'pint'
        # check that we can look for a subset of fields
        fields = test_client.schema.list_fields(fields=['A'])
        names = [f.name for f in fields]
        assert 'B' not in names
        fields = test_client.schema.list_fields(includeDynamic=True)
        names = [f.name for f in fields]
        # check that a stock dynamic field exists
        assert '*_txt_en' in names


    def test_add_copy_field(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        test_client.schema.add_field(name='B', type='string')

        test_client.schema.add_copy_field(source='A', dest='B', maxChars=80)

        cp_fields = test_client.schema.list_copy_fields()
        assert cp_fields[0].source == 'A'
        assert cp_fields[0].dest == 'B'
        assert cp_fields[0].maxChars == 80

    def test_delete_copy_field(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        test_client.schema.add_field(name='B', type='string')

        test_client.schema.add_copy_field(source='A', dest='B')

        cp_fields = test_client.schema.list_copy_fields()
        assert cp_fields[0].source == 'A'
        assert cp_fields[0].dest == 'B'
        test_client.schema.delete_copy_field(source='A', dest='B')
        cp_fields = test_client.schema.list_copy_fields()
        # only copy field should be deleted
        assert len(cp_fields) == 0

    def test_list_copy_fields(self, test_client):
        test_client.schema.add_field(name='A', type='string')
        test_client.schema.add_field(name='B', type='string')
        test_client.schema.add_field(name='C', type='pint')
        test_client.schema.add_field(name='D', type='pint')

        test_client.schema.add_copy_field(source='A', dest='B')
        test_client.schema.add_copy_field(source='C', dest='D')
        cp_fields = test_client.schema.list_copy_fields()
        assert cp_fields[0].source == 'A'
        assert cp_fields[0].dest == 'B'
        assert cp_fields[1].source == 'C'
        assert cp_fields[1].dest == 'D'
        # filter by source field
        ab = test_client.schema.list_copy_fields(source_fl=['A'])
        assert len(ab) == 1
        assert ab[0].source == 'A'
        assert ab[0].dest == 'B'
        # filter by dest field
        cd = test_client.schema.list_copy_fields(dest_fl=['D'])
        assert len(cd) == 1
        assert cd[0].source == 'C'
        assert cd[0].dest == 'D'

    def test_add_field_type(self, test_client):
        test_client.schema.add_field_type(
            name='test_A',
            # handle situations where we need class as kwarg
            klass='solr.TextField'
        )
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        assert 'test_A' in names
        assert field_types[names.index('test_A')]['class'] == 'solr.TextField'

    def test_delete_field_type(self, test_client):
        # create the field type
        test_client.schema.add_field_type(
            name='test_A',
            # handle situations where we need class as kwarg
            klass='solr.TextField'
        )
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        assert 'test_A' in names
        assert field_types[names.index('test_A')]['class'] == 'solr.TextField'
        # delete the field type
        test_client.schema.delete_field_type(name='test_A')
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        assert 'test_A' not in names

    def test_replace_field_type(self, test_client):
        # create the field type
        test_client.schema.add_field_type(
            name='test_A',
            # handle situations where we need class as kwarg
            klass='solr.TextField'
        )
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        assert 'test_A' in names
        assert field_types[names.index('test_A')]['class'] == 'solr.TextField'
        # replace it and check that the change was made
        test_client.schema.replace_field_type(
            name='test_A',
            klass='solr.StrField'
        )
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        assert 'test_A' in names
        assert field_types[names.index('test_A')]['class'] == 'solr.StrField'

    def test_list_field_types(self, test_client):
        # create two field types
        test_client.schema.add_field_type(
            name='test_A',
            klass='solr.StrField'
        )
        test_client.schema.add_field_type(
            name='test_B',
            # handle situations where we need class as kwarg
            klass='solr.TextField'
        )
        field_types = test_client.schema.list_field_types()
        names = [f.name for f in field_types]
        # check that both are in field types, as defined
        assert 'test_A' in names
        assert field_types[names.index('test_A')]['class'] == 'solr.StrField'
        assert 'test_B' in names
        assert field_types[names.index('test_B')]['class'] == 'solr.TextField'

    def test_get_schema(self, test_client):
        schema = test_client.schema.get_schema()
        # check that we have the default schema
        assert schema.name == (
            'default-config' if TEST_SOLR_CONNECTION['MAJOR_SOLR_VERSION'] >= 7
            else 'example-basic'
        )
