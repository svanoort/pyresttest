import resttest
import unittest
import json
import yaml
import math
from binding import Context
from resttest import Test

class TestRestTest(unittest.TestCase):
    """ Tests to test a REST testing framework, how meta is that? """

    def setUp(self):
        pass

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
        self.assertFalse(test.isContextModifier())


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
        self.assertTrue(test.isContextModifier())


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

        cfg = resttest.build_benchmark('what', struct)

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
        benchmark_config = resttest.Benchmark()
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
        benchmark_config = resttest.Benchmark()
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

    def test_metrics_to_tuples(self):
        """ Test method to build list(tuples) from raw metrics """
        array1 = [-1, 5.6, 0]
        array2 = [3.2, -81, 800]
        array3 = [97, -3.4, 'cheese']
        keys = sorted(['blah', 'foo', 'bar'])
        metrics = {keys[0]: array1, keys[1]: array2, keys[2]: array3}

        packed = resttest.metrics_to_tuples(metrics)
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


if __name__ == '__main__':
    unittest.main()