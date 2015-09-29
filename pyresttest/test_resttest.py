import json
import math
import string
import yaml

import resttest
import unittest
from resttest import *

class TestRestTest(unittest.TestCase):
    """ Tests to test overall REST testing framework, how meta is that? """

    def test_analyze_benchmark(self):
        """ Test analyzing benchmarks to compute aggregates """
        benchmark_result = BenchmarkResult()
        benchmark_config = Benchmark()
        benchmark_config.add_metric('request_size').add_metric('request_size','median')
        benchmark_config.add_metric('connect_time')
        benchmark_config.add_metric('total_time', 'mean_harmonic')
        benchmark_config.add_metric('total_time', 'std_deviation')

        benchmark_result.results = {
            'connect_time': [1, 4, 7],
            'request_size': [7, 8, 10],
            'total_time': [0.5, 0.7, 0.9]
        }

        analyzed = analyze_benchmark_results(benchmark_result, benchmark_config)
        self.assertEqual(2, len(analyzed.results.keys()));

        # Check that number of measurements is sane
        distinct_metrics = set([x[0] for x in analyzed.aggregates])
        distinct_aggregates = set([x[1] for x in analyzed.aggregates])
        self.assertEqual(2, len(distinct_metrics))
        self.assertEqual(3, len(distinct_aggregates))
        self.assertEqual(3, len(analyzed.aggregates))

    def test_metrics_to_tuples(self):
        """ Test method to build list(tuples) from raw metrics """
        array1 = [-1, 5.6, 0]
        array2 = [3.2, -81, 800]
        array3 = [97, -3.4, 'cheese']
        keys = sorted(['blah', 'foo', 'bar'])
        metrics = {keys[0]: array1, keys[1]: array2, keys[2]: array3}

        packed = metrics_to_tuples(metrics)
        headers = packed[0]

        # Check header generation
        for x in xrange(0, len(keys)):
            self.assertEqual(keys[x], headers[x])

        # Check data was correctly converted to 2D format, in order of input
        for x in xrange(1, len(array1)+1):
            my_tuple = packed[x]
            self.assertEqual(array1[x-1], my_tuple[0])
            self.assertEqual(array2[x-1], my_tuple[1])
            self.assertEqual(array3[x-1], my_tuple[2])


    def test_parse_headers(self):
        """ Basic header parsing tests """
        headerstring = 'HTTP/1.1 200 OK\r\nDate: Mon, 29 Dec 2014 02:42:33 GMT\r\nExpires: -1\r\nCache-Control: private, max-age=0\r\nContent-Type: text/html; charset=ISO-8859-1\r\nX-XSS-Protection: 1; mode=block\r\nX-Frame-Options: SAMEORIGIN\r\nAlternate-Protocol: 80:quic,p=0.02\r\nTransfer-Encoding: chunked\r\n\r\n'
        header_list = resttest.parse_headers(headerstring)
        header_dict = dict(header_list)

        self.assertTrue(isinstance(header_list, list))
        self.assertEqual('-1', header_dict['expires'])
        self.assertEqual('private, max-age=0', header_dict['cache-control'])
        self.assertEqual(8, len(header_dict))

        # Error cases
        # No headers
        result = resttest.parse_headers("")  # Shouldn't throw exception
        self.assertTrue(isinstance(result, list))
        self.assertEqual(0, len(result))

        # Just the HTTP prefix
        result = resttest.parse_headers('HTTP/1.1 200 OK\r\n\r\n')  # Shouldn't throw exception
        self.assertTrue(isinstance(result, list))
        self.assertEqual(0, len(result))

    def test_parse_headers_multiples(self):
        """ Test headers where there are duplicate values set """
        headerstring = 'HTTP/1.1 200 OK\r\nDate: Mon, 29 Dec 2014 02:42:33 GMT\r\nAccept: text/html\r\nAccept: application/json\r\n\r\n'
        headers = resttest.parse_headers(headerstring)

        self.assertTrue(isinstance(headers, list))
        self.assertEqual(3, len(headers))
        self.assertEqual(('date', 'Mon, 29 Dec 2014 02:42:33 GMT'), headers[0])
        self.assertEqual(('accept', 'text/html'), headers[1])
        self.assertEqual(('accept', 'application/json'), headers[2])

if __name__ == '__main__':
    unittest.main()