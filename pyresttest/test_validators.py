import unittest
import validators
from binding import Context


class ValidatorsTest(unittest.TestCase):
    """ Testing for validators and extract functions """

    def test_dict_query(self):
        """ Test actual query logic """
        mydict = {'key': {'val': 3}}
        query = 'key.val'
        val = validators.MiniJsonExtractor.query_dictionary(query, mydict)
        self.assertEqual(3, val)

        array = [1,2,3]
        mydict = {'key': {'val': array}}
        val = validators.MiniJsonExtractor.query_dictionary(query, mydict)
        self.assertEqual(array, val)

        mydict = {'key': {'v': 'pi'}}
        val = validators.MiniJsonExtractor.query_dictionary(query, mydict)
        self.assertEqual(None, val)

        # Array test
        query = 'key.val.1'
        mydict = {'key': {'val': array}}
        val = validators.MiniJsonExtractor.query_dictionary(query, mydict)
        self.assertEqual(array[1], val)

        # Error cases
        query = 'key.val.5'
        mydict = {'key': {'val': array}}
        val = validators.MiniJsonExtractor.query_dictionary(query, mydict)
        self.assertEqual(None, val)

        query = 'key.val.pi'
        mydict = {'key': {'val': array}}
        val = validators.MiniJsonExtractor.query_dictionary(query, mydict)
        self.assertEqual(None, val)

        # Return the first object?
        query = 'key.0'
        mydict = {'key': {'val': array}}
        val = validators.MiniJsonExtractor.query_dictionary(query, mydict)
        self.assertEqual(None, val)

    def test_parse_extractor_minijson(self):
        config = 'key.val'
        extractor = validators.MiniJsonExtractor.parse(config)
        myjson = '{"key": {"val": 3}}'
        context = Context()
        context.bind_variable('node', 'val')

        extracted = extractor.extract(body=myjson)
        self.assertEqual(3, extracted)
        self.assertEqual(extracted, extractor.extract(body=myjson, context=context))

        try:
            val = extractor.extract(body='[31{]')
            self.fail("Should throw exception on invalid JSON")
        except ValueError:
            pass

        # Templating
        config = {'template': 'key.$node'}
        extract = validators.MiniJsonExtractor.parse(config)
        self.assertEqual(3, extract.extract(myjson, context=context))

    def test_abstract_extractor_parse(self):
        """ Test parsing a basic abstract extractor """
        ext = validators.AbstractExtractor()
        ext = validators.AbstractExtractor.configure_base('val', ext)
        self.assertEqual('val', ext.query)
        self.assertEqual(False, ext.is_templated)

        validators.AbstractExtractor.configure_base({'template': '$var'}, ext)
        self.assertEqual(True, ext.is_templated)
        self.assertEqual('$var', ext.query)

    def test_abstract_extractor_string(self):
        """ Test abstract extractor to_string method """
        ext = validators.AbstractExtractor()
        ext.is_templated = True
        ext.is_header_extractor = True
        ext.is_body_extractor = True
        ext.query = 'gooblyglah'
        ext.extractor_type = 'bleh'
        ext.args = {'cheesy': 'poofs'}

        expected = "Extractor type: {0}, query: {1}, is_templated: {2}, args: {3}".format(ext.extractor_type, ext.query, ext.is_templated, ext.args)
        self.assertEqual(expected, str(ext))

    def test_abstract_extractor_templating(self):
        """ Test that abstract extractors template the query """
        ext = validators.AbstractExtractor()
        ext.query = '$val.vee'
        ext.is_templated = True
        context = Context()
        context.bind_variable('val', 'foo')
        self.assertEqual('$val.vee', ext.templated_query())
        self.assertEqual('foo.vee', ext.templated_query(context=context))

        ext.is_templated = False
        self.assertEqual('$val.vee', ext.templated_query(context=context))

    def test_parse_extractor(self):
        """ Test parsing an extractor using the registry """
        config = 'key.val'
        myjson = '{"key": {"val": 3}}'
        extractor = validators.parse_extractor('jsonpath_mini', config)
        self.assertTrue(isinstance(extractor, validators.AbstractExtractor))
        self.assertEqual(3, extractor.extract(body=myjson))

    def test_get_extractor(self):
        config = {
            'jsonpath_mini': 'key.val',
            'comparator': 'eq',
            'expected': 3
        }
        extractor = validators._get_extractor(config)
        myjson = '{"key": {"val": 3}}'
        extracted = extractor.extract(body=myjson)
        self.assertEqual(3, extracted)

    def test_parse_validator(self):
        """ Test basic parsing using registry """
        config = {
            'jsonpath_mini': 'key.val',
            'comparator': 'eq',
            'expected': 3
        }
        validator = validators.parse_validator('comparator', config)
        myjson = '{"key": {"val": 3}}'
        comp = validator.validate(body=myjson)

        # Try it with templating
        config['jsonpath_mini']={'template':'key.$node'}
        validator = validators.parse_validator('comparator', config)
        context = Context()
        context.bind_variable('node','val')
        comp = validator.validate(myjson, context=context)

    def test_parse_validator_nocomparator(self):
        """ Test that comparator validator with no comparator defaults to eq """
        config = {
            'jsonpath_mini': 'key.val',
            'expected': 3
        }
        validator = validators.parse_validator('assertEqual', config)
        self.assertEqual('eq', validator.comparator_name)
        self.assertEqual(validators.COMPARATORS['eq'], validator.comparator)

    def test_validator_compare_basic(self):
        """ Basic tests of the comparison validators, and templating"""
        config = {
            'jsonpath_mini': 'key.val',
            'comparator': 'eq',
            'expected': 3
        }
        comp_validator = validators.ComparatorValidator.parse(config)
        myjson_pass = '{"id": 3, "key": {"val": 3}}'
        myjson_fail = '{"id": 3, "key": {"val": 4}}'

        self.assertTrue(comp_validator.validate(body=myjson_pass))
        self.assertFalse(comp_validator.validate(body=myjson_fail))

    def test_validator_comparator_templating(self):
        """ Try templating comparator validator """
        config = {
            'jsonpath_mini': {'template': 'key.$node'},
            'comparator': 'eq',
            'expected': 3
        }
        context = Context()
        context.bind_variable('node', 'val')
        myjson_pass = '{"id": 3, "key": {"val": 3}}'
        myjson_fail = '{"id": 3, "key": {"val": 4}}'
        comp = validators.ComparatorValidator.parse(config)

        self.assertTrue(comp.validate(body=myjson_pass, context=context))
        self.assertFalse(comp.validate(body=myjson_fail, context=context))

        # Template expected
        config['expected'] = {'template' : '$id'}
        context.bind_variable('id', 3)
        self.assertTrue(comp.validate(body=myjson_pass, context=context))
        self.assertFalse(comp.validate(body=myjson_fail, context=context))

    def test_validator_comparator_extract(self):
        """ Try comparing two extract expressions """
        config = {
            'jsonpath_mini': 'key.val',
            'comparator': 'eq',
            'expected': {'jsonpath_mini': 'id'}
        }
        myjson_pass = '{"id": 3, "key": {"val": 3}}'
        myjson_fail = '{"id": 3, "key": {"val": 4}}'
        comp = validators.ComparatorValidator.parse(config)
        self.assertTrue(comp.validate(body=myjson_pass))
        failure = comp.validate(body=myjson_fail)
        self.assertFalse(failure)

    def test_validator_error_responses(self):
        config = {
            'jsonpath_mini': 'key.val',
            'comparator': 'eq',
            'expected': 3
        }
        comp = validators.ComparatorValidator.parse(config)
        myjson_fail = '{"id": 3, "key": {"val": 4}}'
        failure = comp.validate(body=myjson_fail)

        # Test the validator failure object handling
        self.assertFalse(failure)
        self.assertEqual(failure.message, 'Comparison failed, evaluating eq(4, 3) returned False')
        self.assertEqual(failure.message, str(failure))
        self.assertTrue(failure.details)
        print "Failure config: "+str(failure.details)
        self.assertEqual(comp, failure.validator)

        failure = comp.validate(body='{"id": 3, "key": {"val": 4}')
        self.assertTrue(isinstance(failure, validators.Failure))

    def test_parse_validator_extracttest(self):
        """ Test parsing for extract test """
        config = {
            'jsonpath_mini': 'key.val',
            'test': 'exists'
        }
        myjson_pass = '{"id": 3, "key": {"val": 3}}'
        myjson_fail = '{"id": 3, "key": {"valley": "wide"}}'
        validator = validators.ExtractTestValidator.parse(config)
        validation_result = validator.validate(body=myjson_pass)
        self.assertTrue(validation_result)

        validation_result = validator.validate(body=myjson_fail)
        self.assertFalse(validation_result)
        self.assertTrue(isinstance(validation_result, validators.Failure))
        self.assertEqual(validation_result.message, "Extract and test validator failed on test: exists(None)")

if __name__ == '__main__':
    unittest.main()