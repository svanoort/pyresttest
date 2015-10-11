import unittest
from parsing import flatten_dictionaries, lowercase_keys, safe_to_bool, safe_to_json


class TestParsing(unittest.TestCase):
    """ Tests for parsing utility functions """

    def test_flatten(self):
        """ Test flattening of lists of dictionaries to single dictionaries """

        # Test happy path: list of single-item dictionaries in
        array = [{"url": "/cheese"}, {"method": "POST"}]
        expected = {"url": "/cheese", "method": "POST"}
        output = flatten_dictionaries(array)
        self.assertTrue(isinstance(output, dict))
        # Test that expected output matches actual
        self.assertFalse(len(set(output.items()) ^ set(expected.items())))

        # Test dictionary input
        array = {"url": "/cheese", "method": "POST"}
        expected = {"url": "/cheese", "method": "POST"}
        output = flatten_dictionaries(array)
        self.assertTrue(isinstance(output, dict))
        # Test that expected output matches actual
        self.assertTrue(len(set(output.items()) ^ set(expected.items())) == 0)

        # Test empty list input
        array = []
        expected = {}
        output = flatten_dictionaries(array)
        self.assertTrue(isinstance(output, dict))
        # Test that expected output matches actual
        self.assertFalse(len(set(output.items()) ^ set(expected.items())))

        # Test empty dictionary input
        array = {}
        expected = {}
        output = flatten_dictionaries(array)
        self.assertTrue(isinstance(output, dict))
        # Test that expected output matches actual
        self.assertFalse(len(set(output.items()) ^ set(expected.items())))

        # Test mixed-size input dictionaries
        array = [{"url": "/cheese"}, {"method": "POST", "foo": "bar"}]
        expected = {"url": "/cheese", "method": "POST", "foo": "bar"}
        output = flatten_dictionaries(array)
        self.assertTrue(isinstance(output, dict))
        # Test that expected output matches actual
        self.assertFalse(len(set(output.items()) ^ set(expected.items())))

    def test_safe_boolean(self):
        """ Test safe conversion to boolean """
        self.assertFalse(safe_to_bool(False))
        self.assertTrue(safe_to_bool(True))
        self.assertTrue(safe_to_bool('True'))
        self.assertTrue(safe_to_bool('true'))
        self.assertTrue(safe_to_bool('truE'))
        self.assertFalse(safe_to_bool('false'))

        # Try things that should throw exceptions
        try:
            boolean = safe_to_bool('fail')
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass  # Good

        try:
            boolean = safe_to_bool([])
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass  # Good

        try:
            boolean = safe_to_bool(None)
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass  # Good

    def test_safe_to_json(self):
        self.assertEqual(u'adj12321nv', safe_to_json(
            bytearray('adj12321nv', 'UTF-8')))
        self.assertEqual(u'5.2', safe_to_json(5.2))

        class Special(object):
            bal = 5.3
            test = 'stuffing'

            def __init__(self):
                self.newval = 'cherries'

        self.assertEqual({'newval': 'cherries'}, safe_to_json(Special()))

    def test_run_configure(self):
        """ Test the configure function use """
        converter = safe_to_bool
        pass

    def test_configure(self):
        """ Do stuff here """
        pass
if __name__ == '__main__':
    unittest.main()
