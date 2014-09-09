import resttest
import unittest
import json
import yaml
import math

class TestRestTest(unittest.TestCase):
    """ Tests to test a REST testing framework, how meta is that? """

    def setUp(self):
        pass

    def test_build_test(self):
        """ Test basic ways of creating test objects from input object structure """

        #Most basic case
        input = {"url": "/ping", "method": "DELETE", "NAME":"foo", "group":"bar", "body":"<xml>input</xml>","headers":{"Accept":"Application/json"}}
        test = resttest.build_test('',input)
        self.assertTrue(test.url == input['url'])
        self.assertTrue(test.method == input['method'])
        self.assertTrue(test.name == input['NAME'])
        self.assertTrue(test.group == input['group'])
        self.assertTrue(test.body == input['body'])
        #Test headers match
        self.assertFalse( set(test.headers.values()) ^ set(input['headers'].values()) )

        #Happy path, only gotcha is that it's a POST, so must accept 200 or 204 response code
        input = {"url": "/ping", "meThod": "POST"}
        test = resttest.build_test('',input)
        self.assertTrue(test.url == input['url'])
        self.assertTrue(test.method == input['meThod'])
        self.assertTrue(test.expected_status == [200,201,204])

        #Test that headers propagate
        input = {"url": "/ping", "method": "GET", "headers" : [{"Accept":"application/json"},{"Accept-Encoding":"gzip"}] }
        test = resttest.build_test('',input)
        expected_headers = {"Accept":"application/json","Accept-Encoding":"gzip"}

        self.assertTrue(test.url == input['url'])
        self.assertTrue(test.method == 'GET')
        self.assertTrue(test.expected_status == [200])
        self.assertTrue(isinstance(test.headers,dict))

        #Test no header mappings differ
        self.assertFalse( set(test.headers.values()) ^ set(expected_headers.values()) )


        #Test expected status propagates and handles conversion to integer
        input = [{"url": "/ping"},{"name": "cheese"},{"expected_status":["200",204,"202"]}]
        test = resttest.build_test('',input)
        self.assertTrue(test.name == "cheese")
        print test.expected_status
        self.assertTrue(test.expected_status == [200,204,202])

    def test_safe_boolean(self):
        """ Test safe conversion to boolean """
        self.assertFalse(resttest.safe_to_bool(False))
        self.assertTrue(resttest.safe_to_bool(True))
        self.assertTrue(resttest.safe_to_bool('True'))
        self.assertTrue(resttest.safe_to_bool('true'))
        self.assertTrue(resttest.safe_to_bool('truE'))
        self.assertFalse(resttest.safe_to_bool('false'))

        #Try things that should throw exceptions
        try:
            boolean = resttest.safe_to_bool('fail')
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass #Good

        try:
            boolean = resttest.safe_to_bool([])
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass #Good

        try:
            boolean = resttest.safe_to_bool(None)
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass #Good


    def test_make_configuration(self):
        """ Test basic configuration parsing """
        input = {"url": "/ping", "method": "DELETE", "NAME":"foo", "group":"bar", "body":"<xml>input</xml>","headers":{"Accept":"Application/json"}}
        test = resttest.make_configuration(input)

        input = {"url": "/ping", "method": "DELETE", "NAME":"foo", "group":"bar", "body":"<xml>input</xml>","headers":{"Accept":"Application/json"}}

        pass

    def test_benchmark_configuration(self):
        """ Test basic parsing of benchmark configuration from YAML """

        struct = [
            {'warmup_runs': 7},
            {'benchmark_runs': '101'},
            {'metrics': ['total_time',
                        {'total_time': 'mean'},
                        {'total_time': 'median'},
                        {'pretransfer_time': 'mean_harmonic'}]
            }];

        cfg = resttest.build_benchmark_config(struct)

        self.assertEqual(7, cfg.warmup_runs)
        self.assertEqual(101, cfg.benchmark_runs)
        self.assertEqual(2, len(cfg.metrics))
        self.assertTrue(len(set(['total_time','pretransfer_time']) ^ cfg.metrics) == 0, msg="Wrong metrics set generated")

        self.assertEqual(1, len(cfg.raw_metrics))
        self.assertTrue(len(set(['total_time']) ^ cfg.raw_metrics) == 0, msg="Wrong raw_metrics generated")

        self.assertEqual(2, len(cfg.aggregated_metrics))
        self.assertEqual(2, len(cfg.aggregated_metrics['total_time']))
        self.assertEqual(1, len(cfg.aggregated_metrics['pretransfer_time']))


    def test_flatten(self):
        """ Test flattening of lists of dictionaries to single dictionaries """

        #Test happy path: list of single-item dictionaries in
        array = [{"url" : "/cheese"}, {"method" : "POST"}]
        expected = {"url" :"/cheese", "method" : "POST"}
        output = resttest.flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual

        #Test dictionary input
        array = {"url" : "/cheese", "method" : "POST"}
        expected = {"url" : "/cheese", "method" : "POST"}
        output = resttest.flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertTrue( len(set(output.items()) ^ set(expected.items())) == 0) #Test that expected output matches actual

        #Test empty list input
        array = []
        expected = {}
        output = resttest.flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual

        #Test empty dictionary input
        array = {}
        expected = {}
        output = resttest.flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual

        #Test mixed-size input dictionaries
        array = [{"url" : "/cheese"}, {"method" : "POST", "foo" : "bar"}]
        expected = {"url" : "/cheese", "method" : "POST", "foo" : "bar"}
        output = resttest.flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual


    def test_median(self):
        """ Test median computation, using a few samples """
        result = resttest.median([0.1])
        result2 = resttest.median([1])
        self.assertEqual(0.1, result)
        self.assertEqual(1, result2)

        # Test multiple eelments
        result = resttest.median([0.1, 0.2, 0.3])
        self.assertEqual(0.2, result)

        # Test averages of 2 values, with different orderings
        result = resttest.median([0.1, 0.2, 0.2, 0.3])
        result2 = resttest.median([0.2, 0.3, 0.2, 0.1])
        self.assertTrue(math.fabs(result - 0.2) < 0.001)
        self.assertTrue(math.fabs(result2 - 0.2) < 0.001)

        # Test averages of integers
        result = resttest.median([1, 2, 3, 4])
        self.assertTrue(math.fabs(float(result) - 2.5) < 0.001)


    def test_std_deviation(self):
        """ Test std deviation computation """
        result = resttest.std_deviation([2, 4, 4, 4, 5, 5, 7, 9])
        self.assertTrue(math.fabs(result - 2.0) < 0.001)

        # Test shuffled
        result2 = resttest.std_deviation([9, 4, 5, 4, 5, 4, 7, 2])
        self.assertTrue(math.fabs(float(result) - float(result2)) < 0.001)

        # Test single value
        result = resttest.std_deviation([1])
        self.assertTrue(math.fabs(float(result) - 0.0) < 0.001)

    def test_harmonic_mean(self):
        """ Test harmonic mean computation """
        function = resttest.AGGREGATES['mean_harmonic']
        result = function([1, 100])
        self.assertTrue(math.fabs(float(result) - float(1.98019802)) < 0.001)


    def test_aggregate_computations(self):
        """ Test running all the aggregates, just to see if they error """
        array = [-1, 5, 2.245, 7]
        for function in resttest.AGGREGATES.values():
            value = function(array)
            self.assertTrue(isinstance(value, int) or isinstance(value, float))


    def test_add_metric(self):
        """ Test the add-metric method for benchmarks """
        benchmark_config = resttest.BenchmarkConfig()
        benchmark_config.add_metric('total_time')
        self.assertTrue('total_time' in benchmark_config.metrics)
        self.assertTrue('total_time' in benchmark_config.raw_metrics)
        self.assertTrue('total_time' not in benchmark_config.aggregated_metrics)

        # Check that adding an aggregate works correctly
        benchmark_config.add_metric('total_time', 'median')
        self.assertTrue('total_time' in benchmark_config.raw_metrics)
        self.assertTrue('total_time' in benchmark_config.aggregated_metrics)

        benchmark_config.add_metric('total_time', 'mean')
        self.assertEqual(2, len(benchmark_config.aggregated_metrics['total_time']))

        # Check that we don't add raw metrics if we do not have to
        benchmark_config.add_metric('connect_time', 'mean')
        self.assertEqual(1, len(benchmark_config.raw_metrics))
        self.assertEqual(2, len(benchmark_config.aggregated_metrics.keys()))
        self.assertEqual(1, len(benchmark_config.aggregated_metrics['connect_time']))

        # Check adding next raw metric in doesn't break things
        benchmark_config.add_metric('redirect_time')
        self.assertEqual(3, len(benchmark_config.metrics))
        self.assertEqual(2, len(benchmark_config.raw_metrics))
        self.assertEqual(2, len(benchmark_config.aggregated_metrics.keys()))



    def test_analyze_benchmark(self):
        """ Test analyzing benchmarks to compute aggregates """
        benchmark_result = resttest.BenchmarkResult()
        benchmark_config = resttest.BenchmarkConfig()
        benchmark_config.add_metric('request_size').add_metric('request_size','median')
        benchmark_config.add_metric('connect_time')
        benchmark_config.add_metric('total_time', 'mean_harmonic')
        benchmark_config.add_metric('total_time', 'std_deviation')

        benchmark_result.results = {
            'connect_time': [1, 4, 7],
            'request_size': [7, 8, 10],
            'total_time': [0.5, 0.7, 0.9]
        }

        analyzed = resttest.analyze_benchmark_results(benchmark_result, benchmark_config)
        self.assertEqual(2, len(analyzed.results.keys()));

        # Check that number of measurements is sane
        distinct_metrics = set([x[0] for x in analyzed.aggregates])
        distinct_aggregates = set([x[1] for x in analyzed.aggregates])
        self.assertEqual(2, len(distinct_metrics))
        self.assertEqual(3, len(distinct_aggregates))
        self.assertEqual(3, len(analyzed.aggregates))


if __name__ == '__main__':
    unittest.main()