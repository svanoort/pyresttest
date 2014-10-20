#!/usr/bin/env python
import os
import sys
import time
import json
import resttest
import unittest
import logging
from multiprocessing import Process
from django.core.management import call_command

#Django testing settings, initial configuration
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")
djangopath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testapp')
sys.path.append(djangopath)

logging.basicConfig(level=logging.WARNING)

""" Full functional testing of REST test suite, using a basic Django-tastypie REST app """
class RestTestCase(unittest.TestCase):
    server_process = None
    prefix = 'http://localhost:8000'

    def setUp(self):
        """ Start a mini Django-tastypie REST webapp with test data for testing REST tests """
        config_args = ('testserver', os.path.join(djangopath,'test_data.json'))
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
        test = resttest.Test()
        test.url = self.prefix + '/api/person/'
        test_response = resttest.run_test(test)
        self.assertTrue(test_response.passed)
        self.assertEqual(200, test_response.response_code)

    def test_detailed_get(self):
        test = resttest.Test()
        test.url = self.prefix + '/api/person/1/'
        test_response = resttest.run_test(test)
        self.assertEqual(True, test_response.passed)
        self.assertEqual(200, test_response.response_code)

    def test_failed_get(self):
        """ Test GET that should fail """
        test = resttest.Test()
        test.url = self.prefix + '/api/person/500/'
        test_response = resttest.run_test(test)
        self.assertEqual(False, test_response.passed)
        self.assertEqual(404, test_response.response_code)

    def test_put_inplace(self):
        """ Test PUT where item already exists """
        test = resttest.Test()
        test.url = self.prefix + '/api/person/1/'
        test.method = u'PUT'
        test.body = '{"first_name": "Gaius","id": 1,"last_name": "Baltar","login": "gbaltar"}'
        test.headers = {u'Content-Type':u'application/json'}
        test_response = resttest.run_test(test)
        self.assertEqual(True, test_response.passed)
        self.assertEqual(200, test_response.response_code)

    def test_put_created(self):
        """ Test PUT where item DOES NOT already exist """
        test = resttest.Test()
        test.url = self.prefix + '/api/person/100/'
        test.method = u'PUT'
        test.expected_status = [200,201,204]
        test.body = '{"first_name": "Willim","last_name": "Adama","login":"theadmiral", "id": 100}'
        test.headers = {u'Content-Type':u'application/json'}
        test_response = resttest.run_test(test)
        self.assertEqual(True, test_response.passed)
        self.assertEqual(201, test_response.response_code)

        # Test it was actually created
        test2 = resttest.Test()
        test2.url = test.url
        test_response2 = resttest.run_test(test2)
        self.assertTrue(test_response2.passed)
        self.assertTrue(u'"last_name": "Adama"' in test_response2.unicode_body())
        self.assertTrue(u'"login": "theadmiral"' in test_response2.unicode_body())

    def test_post(self):
        """ Test POST to create an item """
        test = resttest.Test()
        test.url = self.prefix + '/api/person/'
        test.method = u'POST'
        test.expected_status = [200,201,204]
        test.body = '{"first_name": "Willim","last_name": "Adama","login": "theadmiral"}'
        test.headers = {u'Content-Type':u'application/json'}
        test_response = resttest.run_test(test)
        self.assertEqual(True, test_response.passed)
        self.assertEqual(201, test_response.response_code)

        # Test user was created
        test2 = resttest.Test()
        test2.url = self.prefix + '/api/person/?login=theadmiral'
        test_response2 = resttest.run_test(test2)
        self.assertTrue(test_response2.passed)
        obj = json.loads(str(test_response2.body))
        print json.dumps(obj)

    def test_delete(self):
        """ Try removing an item """
        test = resttest.Test()
        test.url = self.prefix + '/api/person/1/'
        test.expected_status = [200,202,204]
        test.method = u'DELETE'
        test_response = resttest.run_test(test)
        self.assertEqual(True, test_response.passed)
        self.assertEqual(204, test_response.response_code)

        # Verify it's really gone
        test.method = u'GET'
        test.expected_status = [404]
        test_response = resttest.run_test(test)
        self.assertEqual(True, test_response.passed)
        self.assertEqual(404, test_response.response_code)

        # Check it's gone by name
        test2 = resttest.Test()
        test2.url = self.prefix + '/api/person/?first_name__contains=Gaius'
        test_response2 = resttest.run_test(test2)
        self.assertTrue(test_response2.passed)
        self.assertTrue(u'"objects": []' in test_response2.unicode_body())

    def test_benchmark_get(self):
        """ Benchmark basic local get test """
        test = resttest.Test()
        test.url = self.prefix + '/api/person/'
        benchmark_config = resttest.Benchmark();
        benchmark_config.add_metric('total_time').add_metric('total_time','median')
        benchmark_result = resttest.run_benchmark(benchmark_config)
        print "Benchmark - median request time: " + str(benchmark_result.aggregates[0])
        self.assertTrue(benchmark_config.benchmark_runs, len(benchmark_result.results['total_time']))

if __name__ == "__main__":
    unittest.main()