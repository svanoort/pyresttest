#!/usr/bin/env python
import os
import sys
import json
import resttest
import unittest
from multiprocessing import Process

""" Full functional testing of REST test suite, using client-server """

class RestTestCase(unittest.TestCase):
    server_process = None
    prefix = 'http://localhost:8000'

    def setUp(self):
        """ Start a mini Django-tastypie webserver with test data for testing REST tests """
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")

        from django.core.management import execute_from_command_line
        config_args = list()
        config_args.append(sys.argv[0])
        config_args.append('testserver')
        config_args.append('test_data.json')
        proc = Process(target=execute_from_command_line, args=[config_args])
        self.server_process = proc
        proc.start()
        # proc.join()

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
        test.body = '{"first_name": "Willim","last_name": "Adama","login":"theadmiral", "id": 100}'
        test.headers = {u'Content-Type':u'application/json'}
        test_response = resttest.run_test(test)
        self.assertEqual(True, test_response.passed)
        self.assertEqual(200, test_response.response_code)

        # Test it was actually created
        test2 = resttest.Test()
        test2.url = test.url
        test_response2 = resttest.run_test(test2)
        assertTrue(test_response2.passed)
        assertTrue(test_response2.contains('"last_name":"Adama"'))
        assertTrue(test_response2.contains('"login":"theadmiral"'))

    def test_post(self):
        """ Test PUT where item DOES NOT already exist """
        test = resttest.Test()
        test.url = self.prefix + '/api/person/100/'
        test.method = u'PUT'
        test.body = '{"first_name": "Willim","last_name": "Adama","login": "theadmiral"'
        test.headers = {u'Content-Type':u'application/json'}
        test_response = resttest.run_test(test)
        self.assertEqual(True, test_response.passed)
        self.assertEqual(200, test_response.response_code)

        # Test user was created
        test2 = resttest.Test()
        test2.url = self.prefix + '/api/person/?login=theadmiral'
        test_response2 = resttest.run_test(test2)
        assertTrue(test_response2.passed)
        obj = json.loads(test_response2.body)
        print json.dumps(obj)



    def test_delete(self):
        """ Try removing an item """
        test = resttest.Test()
        test.url = self.prefix + '/api/person/1/'
        test.method = u'DELETE'
        test_response = resttest.run_test(test)
        self.assertEqual(True, test_response.passed)
        self.assertEqual(204, test_response.response_code)

        # Verify it's really gone
        test.method = u'GET'
        test.expected_response = [404]
        test_response = resttest.run_test(test)
        self.assertEqual(True, test_response.passed)
        self.assertEqual(404, test_response.response_code)

        # Check it's gone by name
        test2 = resttest.Test()
        test2.url = self.prefix + '/api/person/?first_name__contains=Gaius'
        test_response2 = resttest.run_test(test2)
        assertTrue(test_response2.passed)
        assertTrue(test_response2.contains('"objects": []'))


    def tearDown(self):
        """ Stop the server process """
        self.server_process.terminate()
        self.server_process = None


if __name__ == "__main__":
    unittest.main()