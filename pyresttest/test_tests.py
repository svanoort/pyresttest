# -*- coding: utf-8 -*-

import unittest
import string

from . import tests
from .tests import *
from . import binding
from .binding import Context
from . import contenthandling
from .contenthandling import ContentHandler
from . import generators

PYTHON_MAJOR_VERSION = sys.version_info[0]
if PYTHON_MAJOR_VERSION > 2:
    from unittest import mock
else:
    import mock

# Python 3 compatibility shims
from . import six
from .six import binary_type
from .six import text_type

class TestsTest(unittest.TestCase):
    """ Testing for basic REST test methods, how meta! """

    # Parsing methods
    def test_coerce_to_string(self):
        self.assertEqual(u'1', coerce_to_string(1))
        self.assertEqual(u'stuff', coerce_to_string(u'stuff'))
        self.assertEqual(u'stuff', coerce_to_string('stuff'))
        self.assertEqual(u'st😽uff', coerce_to_string(u'st😽uff'))
        self.assertRaises(TypeError, coerce_to_string, {'key': 'value'})
        self.assertRaises(TypeError, coerce_to_string, None)


    def test_coerce_http_method(self):
        self.assertEqual(u'HEAD', coerce_http_method(u'hEaD'))
        self.assertEqual(u'HEAD', coerce_http_method(b'hEaD'))
        self.assertRaises(TypeError, coerce_http_method, 5)
        self.assertRaises(TypeError, coerce_http_method, None)
        self.assertRaises(TypeError, coerce_http_method, u'')


    def test_coerce_string_to_ascii(self):
        self.assertEqual(b'stuff', coerce_string_to_ascii(u'stuff'))
        self.assertRaises(UnicodeEncodeError, coerce_string_to_ascii, u'st😽uff')
        self.assertRaises(TypeError, coerce_string_to_ascii, 1)
        self.assertRaises(TypeError, coerce_string_to_ascii, None)


    def test_coerce_list_of_ints(self):
        self.assertEqual([1], coerce_list_of_ints(1))
        self.assertEqual([2], coerce_list_of_ints('2'))
        self.assertEqual([18], coerce_list_of_ints(u'18'))
        self.assertEqual([1, 2], coerce_list_of_ints([1, 2]))
        self.assertEqual([1, 2], coerce_list_of_ints([1, '2']))

        try:
            val = coerce_list_of_ints('goober')
            fail("Shouldn't allow coercing a random string to a list of ints")
        except:
            pass

    def test_parse_curloption(self):
        """ Verify issue with curloption handling from https://github.com/svanoort/pyresttest/issues/138 """
        testdefinition = {"url": "/ping", "curl_option_timeout": 14, 'curl_Option_interface': 'doesnotexist'}
        test = Test.parse_test('', testdefinition)
        print(test.curl_options)
        self.assertTrue('TIMEOUT' in test.curl_options)
        self.assertTrue('INTERFACE' in test.curl_options)
        self.assertEqual(14, test.curl_options['TIMEOUT'])
        self.assertEqual('doesnotexist', test.curl_options['INTERFACE'])

    def test_parse_illegalcurloption(self):
        testdefinition = {"url": "/ping", 'curl_Option_special': 'value'}
        try:
            test = Test.parse_test('', testdefinition)
            fail("Error: test parsing should fail when given illegal curl option")
        except ValueError:
            pass

    def test_parse_test(self):
        """ Test basic ways of creating test objects from input object structure """
        # Most basic case
        myinput = {"url": "/ping", "method": "DELETE", "NAME": "foo", "group": "bar",
                 "body": "<xml>input</xml>", "headers": {"Accept": "Application/json"}}
        test = Test.parse_test('', myinput)
        self.assertEqual(test.url,  myinput['url'])
        self.assertEqual(test.method, myinput['method'])
        self.assertEqual(test.name, myinput['NAME'])
        self.assertEqual(test.group, myinput['group'])
        self.assertEqual(test.body, myinput['body'])
        # Test headers match
        self.assertFalse(set(test.headers.values()) ^
                         set(myinput['headers'].values()))

        # Happy path, only gotcha is that it's a POST, so must accept 200 or
        # 204 response code
        myinput = {"url": "/ping", "meThod": "POST"}
        test = Test.parse_test('', myinput)
        self.assertEqual(test.url, myinput['url'])
        self.assertEqual(test.method, myinput['meThod'])
        self.assertEqual(test.expected_status, [200, 201, 204])

        # Authentication
        myinput = {"url": "/ping", "method": "GET",
                 "auth_username": "foo", "auth_password": "bar"}
        test = Test.parse_test('', myinput)
        self.assertEqual('foo', myinput['auth_username'])
        self.assertEqual('bar', myinput['auth_password'])
        self.assertEqual(test.expected_status, [200])

        # Test that headers propagate
        myinput = {"url": "/ping", "method": "GET",
                 "headers": [{"Accept": "application/json"}, {"Accept-Encoding": "gzip"}]}
        test = Test.parse_test('', myinput)
        expected_headers = {"Accept": "application/json",
                            "Accept-Encoding": "gzip"}

        self.assertEqual(test.url, myinput['url'])
        self.assertEqual(test.method, 'GET')
        self.assertEqual(test.expected_status, [200])
        self.assertTrue(isinstance(test.headers, dict))

        # Test no header mappings differ
        self.assertFalse(set(test.headers.values()) ^
                         set(expected_headers.values()))

        # Test expected status propagates and handles conversion to integer
        myinput = [{"url": "/ping"}, {"name": "cheese"},
                 {"expected_status": ["200", 204, "202"]}]
        test = Test.parse_test('', myinput)
        self.assertEqual(test.name, "cheese")
        self.assertEqual(test.expected_status, [200, 204, 202])
        self.assertFalse(test.is_context_modifier())

    def test_parse_nonstandard_http_method(self):
        myinput = {"url": "/ping", "method": "PATCH", "NAME": "foo", "group": "bar",
                   "body": "<xml>input</xml>", "headers": {"Accept": "Application/json"}}
        test = Test.parse_test('', myinput)
        self.assertEqual("PATCH", test.method)

        try:
            myinput['method'] = 1
            test.parse_test('', myinput)
            fail("Should fail to pass a nonstring HTTP method")
        except TypeError:
            pass

        try:
            myinput['method'] = ''
            test.parse_test('', myinput)
            fail("Should fail to pass a nonstring HTTP method")
        except (TypeError, AssertionError):
            pass

    def test_parse_custom_curl(self):
        # Basic case
        myinput = {'url': '/ping', 'name': 'basic',
                   'curl_option_followLocatION': True}
        test = Test.parse_test('', myinput)
        options = test.curl_options
        self.assertEqual(1, len(options))
        self.assertEqual(True, options['FOLLOWLOCATION'])

        # Test parsing with two options
        myinput['curl_option_maxredirs'] = 99
        test = Test.parse_test('', myinput)
        options = test.curl_options
        self.assertEqual(2, len(options))
        self.assertEqual(True, options['FOLLOWLOCATION'])
        self.assertEqual(99, options['MAXREDIRS'])

        # Invalid curl option
        myinput['curl_option_BOGUSOPTION'] = 'i_fail'
        try:
            test.parse_test('', myinput)
            fail("Should throw an exception when invalid curl option used, but didn't!")
        except ValueError:
            pass

    # We can't use version specific skipIf decorator b/c python 2.6 unittest lacks it
    def test_use_custom_curl(self):
        """ Test that test method really does configure correctly """
        if PYTHON_MAJOR_VERSION > 2:
            # In python 3, use of mocks for the curl setopt version (or via setattr)
            # Will not modify the actual curl object... so test fails
            print("Skipping test of CURL configuration for redirects because the mocks fail")
            raise unittest.SkipTest("Skipping test of CURL configuration for redirects because the mocks fail")

        test = Test()
        test.curl_options = {'FOLLOWLOCATION': True, 'MAXREDIRS': 5}
        mock_handle = pycurl.Curl()

        mock_handle.setopt = mock.MagicMock(return_value=True)
        test.configure_curl(curl_handle=mock_handle)

        # print mock_handle.setopt.call_args_list  # Debugging
        mock_handle.setopt.assert_any_call(mock_handle.FOLLOWLOCATION, True)
        mock_handle.setopt.assert_any_call(mock_handle.MAXREDIRS, 5)
        mock_handle.close()

    def test_basic_auth(self):
        """ Test that basic auth configures correctly """
        if PYTHON_MAJOR_VERSION > 2:
            # In python 3, use of mocks for the curl setopt version (or via setattr)
            # Will not modify the actual curl object... so test fails
            print("Skipping test of CURL configuration for basic auth because the mocks fail in Py3")
            return

        test = Test()
        test.auth_username = u'bobbyg'
        test.auth_password = 'password'
        mock_handle = pycurl.Curl()

        mock_handle.setopt = mock.MagicMock(return_value=True)
        test.configure_curl(curl_handle=mock_handle)

        # print mock_handle.setopt.call_args_list  # Debugging
        mock_handle.setopt.assert_any_call(mock_handle.USERPWD, b'bobbyg:password')
        mock_handle.close()

    def test_parse_test_templated_headers(self):
        """ Test parsing with templated headers """

        heads = {"Accept": "Application/json", "$AuthHeader": "$AuthString"}
        templated_heads = {"Accept": "Application/json",
                           "apikey": "magic_passWord"}
        context = Context()
        context.bind_variables(
            {'AuthHeader': 'apikey', 'AuthString': 'magic_passWord'})

        # If this doesn't throw errors we have silent failures
        input_invalid = {"url": "/ping", "method": "DELETE", "NAME": "foo",
                         "group": "bar", "body": "<xml>input</xml>", "headers": 'goat'}
        try:
            test = Test.parse_test('', input_invalid)
            test.fail("Expected error not thrown")
        except TypeError:
            pass

        def assert_dict_eq(dict1, dict2):
            """ Test dicts are equal """
            self.assertEqual(2, len(set(dict1.items()) & set(dict2.items())))

        # Before templating is used
        input = {"url": "/ping", "method": "DELETE", "NAME": "foo",
                 "group": "bar", "body": "<xml>input</xml>", "headers": heads}
        test = Test.parse_test('', input)
        assert_dict_eq(heads, test.headers)
        assert_dict_eq(heads, test.get_headers(context=context))

        # After templating applied
        input_templated = {"url": "/ping", "method": "DELETE", "NAME": "foo",
                           "group": "bar", "body": "<xml>input</xml>", "headers": {'tEmplate': heads}}
        test2 = Test.parse_test('', input_templated)
        assert_dict_eq(heads, test2.get_headers())
        assert_dict_eq(templated_heads, test2.get_headers(context=context))

    def test_parse_test_validators(self):
        """ Test that for a test it can parse the validators section correctly """
        input = {"url": '/test', 'validators': [
            {'comparator': {
                'jsonpath_mini': 'key.val',
                'comparator': 'eq',
                'expected': 3
            }},
            {'extract_test': {'jsonpath_mini': 'key.val', 'test': 'exists'}}
        ]}

        test = Test.parse_test('', input)
        self.assertTrue(test.validators)
        self.assertEqual(2, len(test.validators))
        self.assertTrue(isinstance(
            test.validators[0], validators.ComparatorValidator))
        self.assertTrue(isinstance(
            test.validators[1], validators.ExtractTestValidator))

        # Check the validators really work
        self.assertTrue(test.validators[0].validate(
            '{"id": 3, "key": {"val": 3}}'))

    def test_parse_validators_fail(self):
        """ Test an invalid validator syntax throws exception """
        input = {"url": '/test', 'validators': ['comparator']}
        try:
            test = Test.parse_test('', input)
            self.fail(
                "Should throw exception if not giving a dictionary-type comparator")
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
        test = Test.parse_test('', test_config)
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
            test = Test.parse_test('', test_config)
            self.fail("Should throw an error when doing empty mapping")
        except TypeError:
            pass

        test_config['extract_binds']['id'] = {
            'jsonpath_mini': 'query',
            'test': 'anotherquery'
        }
        try:
            test = Test.parse_test('', test_config)
            self.fail("Should throw an error when given multiple extractors")
        except ValueError as te:
            pass

    def test_parse_validator_comparator(self):
        """ Test parsing a comparator validator """
        test_config = {
            'name': 'Default',
            'url': '/api',
            'validators': [
                {'comparator': {'jsonpath_mini': 'id',
                                'comparator': 'eq',
                                'expected': {'template': '$id'}}}
            ]
        }
        test = Test.parse_test('', test_config)
        self.assertTrue(test.validators)
        self.assertEqual(1, len(test.validators))

        context = Context()
        context.bind_variable('id', 3)

        myjson = '{"id": "3"}'
        failure = test.validators[0].validate(myjson, context=context)
        self.assertTrue(test.validators[0].validate(myjson, context=context))
        self.assertFalse(test.validators[0].validate(myjson))

    def test_parse_validator_extract_test(self):
        """ Tests parsing extract-test validator """
        test_config = {
            'name': 'Default',
            'url': '/api',
            'validators': [
                {'extract_test': {'jsonpath_mini': 'login',
                                  'test': 'exists'}}
            ]
        }
        test = Test.parse_test('', test_config)
        self.assertTrue(test.validators)
        self.assertEqual(1, len(test.validators))

        myjson = '{"login": "testval"}'
        self.assertTrue(test.validators[0].validate(myjson))

    def test_variable_binding(self):
        """ Test that tests successfully bind variables """
        element = 3
        input = [{"url": "/ping"}, {"name": "cheese"},
                 {"expected_status": ["200", 204, "202"]}]
        input.append({"variable_binds": {'var': 'value'}})

        test = Test.parse_test('', input)
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
        context.bind_variables({'id': 9, 'login': 'kvothe'})
        test.set_body(handler)

        templated = test.realize(context=context)
        self.assertEqual(string.Template(handler.content).safe_substitute(context.get_values()),
                         templated.body)

    def test_header_templating(self):
        test = Test()
        head_templated = {'$key': "$val"}
        context = Context()
        context.bind_variables({'key': 'cheese', 'val': 'gouda'})

        # No templating applied
        test.headers = head_templated
        head = test.get_headers()
        self.assertEqual(1, len(head))
        self.assertEqual('$val', head['$key'])

        test.set_headers(head_templated, is_template=True)
        self.assertTrue(test.templates)
        self.assertTrue(test.NAME_HEADERS in test.templates)

        # No context, no templating
        head = test.headers
        self.assertEqual(1, len(head))
        self.assertEqual('$val', head['$key'])

        # Templated with context
        head = test.get_headers(context=context)
        self.assertEqual(1, len(head))
        self.assertEqual('gouda', head['cheese'])

    def test_update_context_variables(self):
        test = Test()
        context = Context()
        context.bind_variable('foo', 'broken')
        test.variable_binds = {'foo': 'correct', 'test': 'value'}
        test.update_context_before(context)
        self.assertEqual('correct', context.get_value('foo'))
        self.assertEqual('value', context.get_value('test'))

    def test_update_context_generators(self):
        """ Test updating context variables using generator """
        test = Test()
        context = Context()
        context.bind_variable('foo', 'broken')
        test.variable_binds = {'foo': 'initial_value'}
        test.generator_binds = {'foo': 'gen'}
        context.add_generator('gen', generators.generator_basic_ids())

        test.update_context_before(context)
        self.assertEqual(1, context.get_value('foo'))
        test.update_context_before(context)
        self.assertEqual(2, context.get_value('foo'))

if __name__ == '__main__':
    unittest.main()
