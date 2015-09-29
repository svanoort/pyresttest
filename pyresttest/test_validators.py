import unittest
import validators
from binding import Context


class ValidatorsTest(unittest.TestCase):
    """ Testing for validators and extract functions """

    def test_validatortest_exists(self):
        func = validators.VALIDATOR_TESTS['exists']
        self.assertTrue(func('blah'))
        self.assertTrue(func(0))
        self.assertTrue(func('False'))
        self.assertTrue(func(False))
        self.assertFalse(func(None))

    def test_validatortest_not_exists(self):
        func = validators.VALIDATOR_TESTS['not_exists']
        self.assertFalse(func('blah'))
        self.assertFalse(func(0))
        self.assertFalse(func('False'))
        self.assertTrue(func(None))


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

        # Mix array array and dictionary
        mydict = [{'key': 'val'}]
        query = '0.key'
        val = validators.MiniJsonExtractor.query_dictionary(query, mydict)
        self.assertEqual('val', val)

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

    def test_header_extractor(self):
        query = 'content-type'
        extractor = validators.HeaderExtractor.parse(query)
        headers = [('content-type', 'application/json')]
        extracted = extractor.extract(body='blahblah', headers=headers)
        self.assertEqual(headers[0][1], extracted)

        # Test case-insensitivity
        query = 'content-Type'
        extractor = validators.HeaderExtractor.parse(query)
        extracted = extractor.extract(body='blahblah', headers=headers)
        self.assertEqual(headers[0][1], extracted)

        # Throws exception if invalid header
        headers = [('foo', 'bar')]
        try:
            extracted = extractor.extract(body='blahblah', headers=headers)
            self.fail("Extractor should throw exception on invalid key")
        except ValueError:
            pass

    def test_header_extractor_duplicatekeys(self):
        # Test for handling of multiple headders
        query = 'content-Type'
        headers = [('content-type', 'application/json'), ('content-type', 'x-json-special')]
        extractor = validators.HeaderExtractor.parse(query)
        extracted = extractor.extract(body='blahblah', headers=headers)
        self.assertTrue(isinstance(extracted, list))
        self.assertEqual(headers[0][1], extracted[0])
        self.assertEqual(headers[1][1], extracted[1])

    def test_parse_header_extractor(self):
        query = 'content-type'
        extractor = validators.parse_extractor('header', query)
        self.assertTrue(isinstance(extractor, validators.HeaderExtractor))
        self.assertTrue(extractor.is_header_extractor)
        self.assertFalse(extractor.is_body_extractor)

    def test_raw_body_extractor(self):
        query = ''
        extractor = validators.parse_extractor('raw_body', None)
        extractor = validators.parse_extractor('raw_body', query)
        self.assertTrue(isinstance(extractor, validators.RawBodyExtractor))
        self.assertTrue(extractor.is_body_extractor)
        self.assertFalse(extractor.is_header_extractor)

        bod = 'j1j21io312j3'
        val = extractor.extract(body=bod, headers='')
        self.assertEqual(bod, val)

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

    def test_abstract_extractor_readableconfig(self):
        """ Test human-readable extractor config string output """
        config = 'key.val'
        extractor = validators.parse_extractor('jsonpath_mini', config)
        expected_string = 'Extractor Type: jsonpath_mini,  Query: "key.val", Templated?: False'
        self.assertEqual(expected_string, extractor.get_readable_config())

        # Check empty context & args uses okay
        context = Context()
        self.assertEqual(expected_string, extractor.get_readable_config(context=context))
        context.bind_variable('foo', 'bar')
        self.assertEqual(expected_string, extractor.get_readable_config(context=context))
        extractor.args = dict()
        self.assertEqual(expected_string, extractor.get_readable_config(context=context))

        # Check args output is handled correctly
        extractor.args = {'caseSensitive': True}
        self.assertEqual(expected_string+", Args: "+str(extractor.args), extractor.get_readable_config(context=context))

        # Check template handling is okay
        config = {'template': 'key.$templated'}
        context.bind_variable('templated', 'val')
        extractor = validators.parse_extractor('jsonpath_mini', config)
        expected_string = 'Extractor Type: jsonpath_mini,  Query: "key.val", Templated?: True'
        self.assertEqual(expected_string, extractor.get_readable_config(context=context))


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

    def test_validator_compare_eq(self):
        """ Basic test of the equality validator"""
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

    def test_validator_compare_ne(self):
        """ Basic test of the inequality validator"""
        config = {
            'jsonpath_mini': 'key.val',
            'comparator': 'ne',
            'expected': 3
        }
        comp_validator = validators.ComparatorValidator.parse(config)
        myjson_pass = '{"id": 3, "key": {"val": 4}}'
        myjson_fail = '{"id": 3, "key": {"val": 3}}'

        self.assertTrue(comp_validator.validate(body=myjson_pass))
        self.assertFalse(comp_validator.validate(body=myjson_fail))

    def test_validator_compare_not_equals(self):
        """ Basic test of the inequality validator alias"""
        config = {
            'jsonpath_mini': 'key.val',
            'comparator': 'not_equals',
            'expected': 3
        }
        comp_validator = validators.ComparatorValidator.parse(config)
        myjson_pass = '{"id": 3, "key": {"val": 4}}'
        myjson_fail = '{"id": 3, "key": {"val": 3}}'

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
        self.assertEqual(failure.failure_type, validators.FAILURE_VALIDATOR_FAILED)
        expected_details = 'Extractor: Extractor Type: jsonpath_mini,  Query: "key.val", Templated?: False'
        self.assertEqual(expected_details, failure.details)
        print("Failure config: "+str(failure.details))
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