#!/usr/bin/env python
import os
import sys
import time
import json
import unittest
import logging
from multiprocessing import Process

from django.core.management import call_command

from . import tests
from .tests import Test
from . import benchmarks
from . import binding
from .binding import Context
from . import resttest
from . import validators

# Python 2/3 compat shims
from . import six
from .six import text_type
from .six import binary_type

# Django testing settings, initial configuration
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")
djangopath = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'testapp')
sys.path.append(djangopath)

logging.basicConfig(level=logging.WARNING)

""" Full functional testing of REST test suite, using a basic Django-tastypie REST app """


class RestTestCase(unittest.TestCase):
    server_process = None
    prefix = 'http://localhost:8000'

    def setUp(self):
        """ Start a mini Django-tastypie REST webapp with test data for testing REST tests """
        config_args = ('testserver', os.path.join(
            djangopath, 'test_data.json'))
        proc = Process(target=call_command, args=config_args)
        proc.start()
        self.server_process = proc
        time.sleep(1)  # Allows time for server startup

    def tearDown(self):
        """ Stop the server process """
        self.server_process.terminate()
        self.server_process = None

    def test_get(self):
        """ Basic local get test """
        test = Test()
        test.url = self.prefix + '/api/person/'
        test_response = test.execute_macro()
        self.assertTrue(test_response.passed)
        self.assertEqual(200, test_response.response_code)

    def test_head(self):
        """ Calls github API to test the HEAD method, ugly but Django tastypie won't support it """
        test = Test()
        test.url = 'https://api.github.com/users/svanoort'
        test_response = test.execute_macro()
        self.assertTrue(test_response.passed)
        self.assertEqual(200, test_response.response_code)
        print("Github API response headers: \n{0}".format(test_response.response_headers))
        self.assertTrue(test_response.response_headers)

    def test_patch(self):
        """ Basic local get test """
        test = Test()
        test.url = self.prefix + '/api/person/2/'
        test.method = 'PATCH'
        test.body = '{"login":"special"}'
        test.headers = {u'Content-Type': u'application/json',
                        u'X-HTTP-Method-Override': u'PATCH'}
        test.expected_status = [202]  # Django returns 202
        test_response = test.execute_macro()
        self.assertTrue(test_response.passed)
        #self.assertEqual(202, test_response.response_code)

    def test_get_redirect(self):
        """ Basic local get test """
        test = Test()
        test.curl_options = {'FOLLOWLOCATION': True}
        test.url = self.prefix + '/api/person'
        test_response = test.execute_macro()
        self.assertTrue(test_response.passed)
        self.assertEqual(200, test_response.response_code)

    def test_get_validators(self):
        """ Test that validators work correctly """
        test = Test()
        test.url = self.prefix + '/api/person/'

        # Validators need library calls to configure them
        test.validators = list()
        cfg_exists = {'jsonpath_mini': "objects.0", 'test': 'exists'}
        test.validators.append(
            validators.parse_validator('extract_test', cfg_exists))
        cfg_exists_0 = {'jsonpath_mini': "meta.offset", 'test': 'exists'}
        test.validators.append(validators.parse_validator(
            'extract_test', cfg_exists_0))
        cfg_not_exists = {'jsonpath_mini': "objects.100", 'test': 'not_exists'}
        test.validators.append(validators.parse_validator(
            'extract_test', cfg_not_exists))
        cfg_compare_login = {
            'jsonpath_mini': 'objects.0.login', 'expected': 'gbaltar'}
        test.validators.append(validators.parse_validator(
            'compare', cfg_compare_login))
        cfg_compare_id = {'jsonpath_mini': 'objects.1.id',
                          'comparator': 'gt', 'expected': -1}
        test.validators.append(
            validators.parse_validator('compare', cfg_compare_id))

        test_response = test.execute_macro()
        for failure in test_response.failures:
            print("REAL FAILURE")
            print("Test Failure, failure type: {0}, Reason: {1}".format(
                failure.failure_type, failure.message))
            if failure.details:
                print("Validator/Error details: " + str(failure.details))
        self.assertFalse(test_response.failures)
        self.assertTrue(test_response.passed)

    def test_get_validators_fail(self):
        """ Test validators that should fail """
        test = Test()
        test.url = self.prefix + '/api/person/'
        test.validators = list()
        cfg_exists = {'jsonpath_mini': "objects.500", 'test': 'exists'}
        test.validators.append(
            validators.parse_validator('extract_test', cfg_exists))
        cfg_not_exists = {'jsonpath_mini': "objects.1", 'test': 'not_exists'}
        test.validators.append(validators.parse_validator(
            'extract_test', cfg_not_exists))
        cfg_compare = {'jsonpath_mini': "objects.1.last_name",
                       'expected': 'NotJenkins'}
        test.validators.append(
            validators.parse_validator('compare', cfg_compare))
        test_response = test.execute_macro()
        self.assertFalse(test_response.passed)
        self.assertTrue(test_response.failures)
        self.assertEqual(3, len(test_response.failures))

    def test_detailed_get(self):
        test = Test()
        test.url = self.prefix + '/api/person/1/'
        test_response = test.execute_macro()
        self.assertEqual(True, test_response.passed)
        self.assertEqual(200, test_response.response_code)

    def test_header_extraction(self):
        test = Test()
        test.url = self.prefix + '/api/person/1/'
        key1 = 'server-header'
        key2 = 'server-header-mixedcase'

        test.extract_binds = {
            key1: validators.HeaderExtractor.parse('server'),
            # Verify case-insensitive behavior
            key2: validators.HeaderExtractor.parse('sErVer')
        }
        my_context = Context()
        test_response = test.execute_macro(context=my_context)
        val1 = my_context.get_value(key1)
        val2 = my_context.get_value(key2)
        self.assertEqual(val1, val2)
        self.assertTrue('wsgi' in val1.lower())
        self.assertTrue('wsgi' in val2.lower())

    def test_header_validators(self):
        test = Test()
        test.url = self.prefix + '/api/person/1/'
        config = {
            'header': 'server',
            'comparator': 'contains',
            'expected': 'WSGI'
        }
        test.validators = list()
        test.validators.append(
            validators.parse_validator('comparator', config))
        result = test.execute_macro()

        if result.failures:
            for fail in result.failures:
                print(fail)
        self.assertTrue(result.passed)

    def test_failed_get(self):
        """ Test GET that should fail """
        test = Test()
        test.url = self.prefix + '/api/person/500/'
        test_response = test.execute_macro()
        self.assertEqual(False, test_response.passed)
        self.assertEqual(404, test_response.response_code)

    def test_put_inplace(self):
        """ Test PUT where item already exists """
        test = Test()
        test.url = self.prefix + '/api/person/1/'
        test.method = u'PUT'
        test.body = '{"first_name": "Gaius","id": 1,"last_name": "Baltar","login": "gbaltar"}'
        test.headers = {u'Content-Type': u'application/json'}
        test_response = test.execute_macro()
        self.assertEqual(True, test_response.passed)
        self.assertEqual(200, test_response.response_code)

    def test_put_created(self):
        """ Test PUT where item DOES NOT already exist """
        test = Test()
        test.url = self.prefix + '/api/person/100/'
        test.method = u'PUT'
        test.expected_status = [200, 201, 204]
        test.body = '{"first_name": "Willim","last_name": "Adama","login":"theadmiral", "id": 100}'
        test.headers = {u'Content-Type': u'application/json'}
        test_response = test.execute_macro()
        self.assertEqual(True, test_response.passed)
        self.assertEqual(201, test_response.response_code)

        # Test it was actually created
        test2 = Test()
        test2.url = test.url
        test_response2 = test2.execute_macro()
        self.assertTrue(test_response2.passed)
        self.assertTrue(
            u'"last_name": "Adama"' in test_response2.body.decode('UTF-8'))
        self.assertTrue(
            u'"login": "theadmiral"' in test_response2.body.decode('UTF-8'))

    def test_post(self):
        """ Test POST to create an item """
        test = Test()
        test.url = self.prefix + '/api/person/'
        test.method = u'POST'
        test.expected_status = [200, 201, 204]
        test.body = '{"first_name": "Willim","last_name": "Adama","login": "theadmiral"}'
        test.headers = {u'Content-Type': u'application/json'}
        test_response = test.execute_macro()
        self.assertEqual(True, test_response.passed)
        self.assertEqual(201, test_response.response_code)

        # Test user was created
        test2 = Test()
        test2.url = self.prefix + '/api/person/?login=theadmiral'
        test_response2 = test2.execute_macro()
        self.assertTrue(test_response2.passed)

        # Test JSON load/dump round trip on body
        bod = test_response2.body
        if isinstance(bod, binary_type):
            bod = text_type(bod, 'utf-8')
        print(json.dumps(json.loads(bod)))


    def test_delete(self):
        """ Try removing an item """
        test = Test()
        test.url = self.prefix + '/api/person/1/'
        test.expected_status = [200, 202, 204]
        test.method = u'DELETE'
        test_response = test.execute_macro()
        self.assertEqual(True, test_response.passed)
        self.assertEqual(204, test_response.response_code)

        # Verify it's really gone
        test.method = u'GET'
        test.expected_status = [404]
        test_response = test.execute_macro()
        self.assertEqual(True, test_response.passed)
        self.assertEqual(404, test_response.response_code)

        # Check it's gone by name
        test2 = Test()
        test2.url = self.prefix + '/api/person/?first_name__contains=Gaius'
        test_response2 = test2.execute_macro()
        self.assertTrue(test_response2.passed)
        self.assertTrue(u'"objects": []' in test_response2.body.decode('UTF-8'))

    def test_full_context_use(self):
        """ Read and execute test set  with context use, from file """

        # Get absolute path to test file, in the same folder as this test
        path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), 'content-test.yaml')
        print(path)
        tests = resttest.parse_testsets('http://localhost:8000', resttest.read_test_file(
            path), working_directory=os.path.dirname(os.path.realpath(__file__)))
        failures = resttest.run_testsets(tests)
        self.assertTrue(
            failures == 0, 'Simple tests failed where success expected')

    def test_unicode_use(self):
        """ Read and execute test set  with context use, from file """

        # Get absolute path to test file, in the same folder as this test
        path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), 'unicode-test.yaml')
        print(path)
        tests = resttest.parse_testsets('http://localhost:8000', resttest.read_test_file(
            path), working_directory=os.path.dirname(os.path.realpath(__file__)))
        failures = resttest.run_testsets(tests)
        self.assertTrue(
            failures == 0, 'Simple tests failed where success expected')

    def test_benchmark_get(self):
        """ Benchmark basic local get test """
        benchmark_config = benchmarks.Benchmark()
        benchmark_config.url = self.prefix + '/api/person/'
        benchmark_config.add_metric(
            'total_time').add_metric('total_time', 'median')
        benchmark_result = benchmark_config.execute_macro()
        print("Benchmark - median request time: " +
              str(benchmark_result.aggregates[0]))
        self.assertTrue(benchmark_config.benchmark_runs, len(
            benchmark_result.results['total_time']))

    def test_use_validator_ext_jsonschema(self):
        try:
            import jsonschema           
        except ImportError:
            print("Skipping jsonschema import test because library absent")
            raise unittest.SkipTest("JSONSchema module absent")
        # Serious hack dumping the schema in local directory to allow executing it this way
        # But otherwise kind of painful
        path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), 'testapp/schema_test.yaml')
        print(path)
        tests = resttest.parse_testsets('http://localhost:8000', resttest.read_test_file(
            path), working_directory=os.path.dirname(os.path.realpath(__file__)))
        failures = resttest.run_testsets(tests)
        self.assertTrue(
            failures == 0, 'Simple tests failed where success expected')

    def test_use_validators_jmespath_fail(self):
        try:
            import jmespath            
        except ImportError:
            print("Skipping jmespath import test because library absent")
            raise unittest.SkipTest("JMESPath module absent")   

        """ Test validators that should fail """
        test = Test()
        test.url = self.prefix + '/api/person/'
        test.validators = list()
        cfg_exists = {'jmespath': 'objects[500]', 'test': 'exists'}
        test.validators.append(
            validators.parse_validator('extract_test', cfg_exists))
        cfg_not_exists = {'jmespath': "objects[1]", 'test': 'not_exists'}
        test.validators.append(validators.parse_validator(
            'extract_test', cfg_not_exists))
        cfg_compare = {'jmespath': "objects[1].last_name",
                       'expected': 'NotJenkins'}
        test.validators.append(
            validators.parse_validator('compare', cfg_compare))
        test_response = test.execute_macro()
        self.assertFalse(test_response.passed)
        self.assertTrue(test_response.failures)
        self.assertEqual(3, len(test_response.failures))

    def test_get_validators_jmespath(self):
        """ Test that validators work correctly """
        test = Test()
        test.url = self.prefix + '/api/person/'

        # Validators need library calls to configure them
        test.validators = list()
        cfg_exists = {'jmespath': "objects[0]", 'test': 'exists'}
        test.validators.append(
            validators.parse_validator('extract_test', cfg_exists))
        cfg_exists_0 = {'jmespath': "meta.offset", 'test': 'exists'}
        test.validators.append(validators.parse_validator(
            'extract_test', cfg_exists_0))
        cfg_not_exists = {'jmespath': "objects[100]", 'test': 'not_exists'}
        test.validators.append(validators.parse_validator(
            'extract_test', cfg_not_exists))
        cfg_compare_login = {
            'jmespath': 'objects[0].login', 'expected': 'gbaltar'}
        test.validators.append(validators.parse_validator(
            'compare', cfg_compare_login))
        cfg_compare_id = {'jmespath': 'objects[1].id',
                          'comparator': 'gt', 'expected': -1}
        test.validators.append(
            validators.parse_validator('compare', cfg_compare_id))

        test_response = test.execute_macro()
        for failure in test_response.failures:
            print("REAL FAILURE")
            print("Test Failure, failure type: {0}, Reason: {1}".format(
                failure.failure_type, failure.message))
            if failure.details:
                print("Validator/Error details: " + str(failure.details))
        self.assertFalse(test_response.failures)
        self.assertTrue(test_response.passed)


if __name__ == "__main__":
    unittest.main()
