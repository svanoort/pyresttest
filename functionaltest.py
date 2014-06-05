#!/usr/bin/env python
import os
import sys
import resttest
import unittest
from multiprocessing import Process

''' Full functional testing of REST test suite, using client-server '''

class RestTestCase(unittest.TestCase):
    server_process = None

    def setUp(self):
        ''' Start a mini Django-tastypie webserver with test data for testing REST tests '''
        proc = Process(target=start_server, args=(config_args))
        self.server_process = proc
        proc.start()
        # proc.join()

    def test_get(self):
        pass

    def tearDown(self):
        ''' Stop the server process '''
        self.server_process.terminate()
        self.server_process = None



def start_server(my_args):
    execute_from_command_line(my_args)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")

    from django.core.management import execute_from_command_line
    global config_args
    config_args = list()
    config_args.append(sys.argv[0])
    config_args.append('testserver')
    config_args.append('test_data.json')
    unittest.main()