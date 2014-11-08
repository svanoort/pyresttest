import unittest
import string
from tests import *
from binding import Context
from contenthandling import ContentHandler
import generators

class TestsTest(unittest.TestCase):
    """ Testing for basic rest test methods """

    def test_build_test(self):
        """ Test basic ways of creating test objects from input object structure """
        #Most basic case
        input = {"url": "/ping", "method": "DELETE", "NAME":"foo", "group":"bar", "body":"<xml>input</xml>","headers":{"Accept":"Application/json"}}
        test = Test.build_test('',input)
        self.assertTrue(test.url == input['url'])
        self.assertTrue(test.method == input['method'])
        self.assertTrue(test.name == input['NAME'])
        self.assertTrue(test.group == input['group'])
        self.assertTrue(test.body == input['body'])
        #Test headers match
        self.assertFalse( set(test.headers.values()) ^ set(input['headers'].values()) )

        #Happy path, only gotcha is that it's a POST, so must accept 200 or 204 response code
        input = {"url": "/ping", "meThod": "POST"}
        test = Test.build_test('',input)
        self.assertTrue(test.url == input['url'])
        self.assertTrue(test.method == input['meThod'])
        self.assertTrue(test.expected_status == [200,201,204])

        #Test that headers propagate
        input = {"url": "/ping", "method": "GET", "headers" : [{"Accept":"application/json"},{"Accept-Encoding":"gzip"}] }
        test = Test.build_test('',input)
        expected_headers = {"Accept":"application/json","Accept-Encoding":"gzip"}

        self.assertTrue(test.url == input['url'])
        self.assertTrue(test.method == 'GET')
        self.assertTrue(test.expected_status == [200])
        self.assertTrue(isinstance(test.headers,dict))

        #Test no header mappings differ
        self.assertFalse( set(test.headers.values()) ^ set(expected_headers.values()) )


        #Test expected status propagates and handles conversion to integer
        input = [{"url": "/ping"},{"name": "cheese"},{"expected_status":["200",204,"202"]}]
        test = Test.build_test('',input)
        self.assertTrue(test.name == "cheese")
        self.assertTrue(test.expected_status == [200,204,202])
        self.assertFalse(test.is_context_modifier())

    def test_parse_test_validators(self):
        """ Test that for a test it can parse the validators section correctly """
        input = {"url": '/test', 'validators' : [
            {'comparator': {
                'jsonpath_mini': 'key.val',
                'comparator': 'eq',
                'expected': 3
            }},
            {'extract_test': {'jsonpath_mini': 'key.val', 'test':'exists'}}
        ]}

        test = Test.build_test('',input)
        self.assertTrue(test.validators)
        self.assertEqual(2, len(test.validators))
        self.assertTrue(isinstance(test.validators[0], validators.ComparatorValidator))
        self.assertTrue(isinstance(test.validators[1], validators.ExtractTestValidator))

        # Check the validators really work
        self.assertTrue(test.validators[0].validate('{"id": 3, "key": {"val": 3}}'))

    def test_parse_validators_fail(self):
        """ Test an invalid validator syntax throws exception """
        input = {"url": '/test', 'validators' : ['comparator']}
        try:
            test = Test.build_test('', input)
            self.fail("Should throw exception if not giving a dictionary-type comparator")
        except TypeError:
            pass

    def test_parse_extractor_bind(self):
        """ Test parsing of extractors """
        test_config = {
            "url": '/api',
            'extract_binds': {
                'id': {'jsonpath_mini': 'idfield'},
                'name': {'jsonpath_mini': 'firstname'}
            }
        }
        test = Test.build_test('', test_config)
        self.assertTrue(test.extract_binds)
        self.assertEqual(2, len(test.extract_binds))
        self.assertTrue('id' in test.extract_binds)
        self.assertTrue('name' in test.extract_binds)

        # Test extractors config'd correctly for extraction
        myjson = '{"idfield": 3, "firstname": "bob"}'
        extracted = test.extract_binds['id'].extract(myjson)
        self.assertEqual(3, extracted)

        extracted = test.extract_binds['name'].extract(myjson)
        self.assertEqual('bob', extracted)

    def test_parse_extractor_errors(self):
        """ Test that expected errors are thrown on parsing """
        test_config = {
            "url": '/api',
            'extract_binds': {'id': {}}
        }
        try:
            test = Test.build_test('', test_config)
            self.fail("Should throw an error when doing empty mapping")
        except TypeError:
            pass

        test_config['extract_binds']['id'] = {
            'jsonpath_mini': 'query',
            'test':'anotherquery'
        }
        try:
            test = Test.build_test('', test_config)
            self.fail("Should throw an error when given multiple extractors")
        except ValueError as te:
            pass

    def test_variable_binding(self):
        """ Test that tests successfully bind variables """
        element = 3
        input = [{"url": "/ping"},{"name": "cheese"},{"expected_status":["200",204,"202"]}]
        input.append({"variable_binds":{'var':'value'}})

        test = Test.build_test('', input)
        binds = test.variable_binds
        self.assertEqual(1, len(binds))
        self.assertEqual('value', binds['var'])

        # Test that updates context correctly
        context = Context()
        test.update_context_before(context)
        self.assertEqual('value', context.get_value('var'))
        self.assertTrue(test.is_context_modifier())

    def test_test_url_templating(self):
        test = Test()
        test.set_url('$cheese', isTemplate=True)
        self.assertTrue(test.is_dynamic())
        self.assertEqual('$cheese', test.get_url())
        self.assertTrue(test.templates['url'])

        context = Context()
        context.bind_variable('cheese', 'stilton')
        self.assertEqual('stilton', test.get_url(context=context))

        realized = test.realize(context)
        self.assertEqual('stilton', realized.url)

    def test_test_content_templating(self):
        test = Test()
        handler = ContentHandler()
        handler.is_template_content = True
        handler.content = '{"first_name": "Gaius","id": "$id","last_name": "Baltar","login": "$login"}'
        context = Context()
        context.bind_variables({'id':9, 'login':'kvothe'})
        test.set_body(handler)

        templated = test.realize(context=context)
        self.assertEqual(string.Template(handler.content).safe_substitute(context.get_values()),
            templated.body)

    def test_update_context_variables(self):
        test = Test()
        context = Context()
        context.bind_variable('foo','broken')
        test.variable_binds = {'foo':'correct', 'test':'value'}
        test.update_context_before(context)
        self.assertEqual('correct', context.get_value('foo'))
        self.assertEqual('value', context.get_value('test'))

    def test_update_context_generators(self):
        """ Test updating context variables using generator """
        test = Test()
        context = Context()
        context.bind_variable('foo','broken')
        test.variable_binds = {'foo': 'initial_value'}
        test.generator_binds = {'foo': 'gen'}
        context.add_generator('gen', generators.generator_basic_ids())

        test.update_context_before(context)
        self.assertEqual(1, context.get_value('foo'))
        test.update_context_before(context)
        self.assertEqual(2, context.get_value('foo'))

if __name__ == '__main__':
    unittest.main()