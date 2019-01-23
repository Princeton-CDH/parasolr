from django.test import TestCase


class Test(TestCase):

    def test_basic(self):
        '''Ensure that testing harness works.'''
        assert 1 + 1 == 2