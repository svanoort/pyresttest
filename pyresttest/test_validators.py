import unittest
import validators
from binding import Context


class ValidatorsTest(unittest.TestCase):
    """ Testing for validators and extract functions """

    def test_dict_query(self):
        """ Test actual query logic """
        mydict = {'key': {'val': 3}}
        query = 'key.val'
        val = validators.query_dictionary(query, mydict)
        self.assertEqual(3, val)

        array = [1,2,3]
        mydict = {'key': {'val': array}}
        val = validators.query_dictionary(query, mydict)
        self.assertEqual(array, val)

        mydict = {'key': {'v': 'pi'}}
        val = validators.query_dictionary(query, mydict)
        self.assertEqual(None, val)

        # Array test
        query = 'key.val.1'
        mydict = {'key': {'val': array}}
        val = validators.query_dictionary(query, mydict)
        self.assertEqual(array[1], val)

        # Templating test
        query = 'key.$node'
        mydict = {'key': {'val': 3}}
        context = Context()
        context.bind_variable('node', 'val')
        val = validators.query_dictionary(query, mydict, context=context, isTemplate=True)
        self.assertEqual(3, val)

        # Error cases
        query = 'key.val.5'
        mydict = {'key': {'val': array}}
        val = validators.query_dictionary(query, mydict)
        self.assertEqual(None, val)

        query = 'key.val.pi'
        mydict = {'key': {'val': array}}
        val = validators.query_dictionary(query, mydict)
        self.assertEqual(None, val)

        # Return the first object?
        query = 'key.0'
        mydict = {'key': {'val': array}}
        val = validators.query_dictionary(query, mydict)
        self.assertEqual(None, val)

    def test_parse_extractor_minijson(self):
        config = 'key.val'
        extract_fn = validators.parse_extractor_minijson(config)
        myjson = '{"key": {"val": 3}}'
        context = Context()
        context.bind_variable('node', 'val')

        extracted = extract_fn(myjson)
        self.assertEqual(3, extracted)
        self.assertEqual(extracted, extract_fn(myjson, context))

        self.assertEqual(None, extract_fn('[31{]'))

        # Templating
        config = {'template': 'key.$node'}
        extract_fn = validators.parse_extractor_minijson(config)
        self.assertEqual(3, extract_fn(myjson, context=context))

    def test_validator_compare_basic(self):
        """ Basic tests of the comparison validators """
        config = {
            'jsonpath_mini': 'key.val',
            'comparator': 'eq',
            'expected': 3
        }
        comp_fn = validators.parse_comparator_validator(config)
        myjson = "{'key': {'val': 3}}"
        self.assertTrue(comp_fn(myjson))




if __name__ == '__main__':
    unittest.main()