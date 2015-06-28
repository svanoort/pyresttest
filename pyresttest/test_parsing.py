import unittest
from parsing import flatten_dictionaries, lowercase_keys, safe_to_bool, resolve_variable

class TestParsing(unittest.TestCase):
    """ Tests for parsing utility functions """

    def test_resolve_variable(self):
        variable = 'cheese'

        # Illegal scopes
        self.assertTrue(resolve_variable(variable, 0) is None)
        self.assertTrue(resolve_variable(variable, None) is None)
        self.assertTrue(resolve_variable(variable, dict()) is None)

        # Simple scope test
        scopes = [{variable:'cheddar'}]
        self.assertEqual('cheddar', resolve_variable(variable, scopes))

        # Complex scope test
        scopes = [{'nope': 'morenope'},{variable:'cheddar'}]
        self.assertEqual('cheddar', resolve_variable(variable, scopes))

        # Overridden scopes
        scopes = [{variable: 'wensleydale'},{variable:'cheddar'}]
        self.assertEqual('wensleydale', resolve_variable(variable, scopes))

        # Defaulting
        scopes = [{variable: 'wensleydale'},{variable:'cheddar'}]
        self.assertEqual('chicken', resolve_variable('meat', scopes ,'chicken'))


    def test_flatten(self):
        """ Test flattening of lists of dictionaries to single dictionaries """

        #Test happy path: list of single-item dictionaries in
        array = [{"url" : "/cheese"}, {"method" : "POST"}]
        expected = {"url" :"/cheese", "method" : "POST"}
        output = flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual

        #Test dictionary input
        array = {"url" : "/cheese", "method" : "POST"}
        expected = {"url" : "/cheese", "method" : "POST"}
        output = flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertTrue( len(set(output.items()) ^ set(expected.items())) == 0) #Test that expected output matches actual

        #Test empty list input
        array = []
        expected = {}
        output = flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual

        #Test empty dictionary input
        array = {}
        expected = {}
        output = flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual

        #Test mixed-size input dictionaries
        array = [{"url" : "/cheese"}, {"method" : "POST", "foo" : "bar"}]
        expected = {"url" : "/cheese", "method" : "POST", "foo" : "bar"}
        output = flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual

    def test_safe_boolean(self):
        """ Test safe conversion to boolean """
        self.assertFalse(safe_to_bool(False))
        self.assertTrue(safe_to_bool(True))
        self.assertTrue(safe_to_bool('True'))
        self.assertTrue(safe_to_bool('true'))
        self.assertTrue(safe_to_bool('truE'))
        self.assertFalse(safe_to_bool('false'))

        #Try things that should throw exceptions
        try:
            boolean = safe_to_bool('fail')
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass #Good

        try:
            boolean = safe_to_bool([])
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass #Good

        try:
            boolean = safe_to_bool(None)
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass #Good




if __name__ == '__main__':
    unittest.main()