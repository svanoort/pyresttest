import unittest
from benchmarks import *

class BenchmarkTest(unittest.TestCase):
    """ Tests for benchmark container class """

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

        cfg = build_benchmark('what', struct)

        self.assertEqual(7, cfg.warmup_runs)
        self.assertEqual(101, cfg.benchmark_runs)
        self.assertEqual(2, len(cfg.metrics))
        self.assertTrue(len(set(['total_time','pretransfer_time']) ^ cfg.metrics) == 0, msg="Wrong metrics set generated")

        self.assertEqual(1, len(cfg.raw_metrics))
        self.assertTrue(len(set(['total_time']) ^ cfg.raw_metrics) == 0, msg="Wrong raw_metrics generated")

        self.assertEqual(2, len(cfg.aggregated_metrics))
        self.assertEqual(2, len(cfg.aggregated_metrics['total_time']))
        self.assertEqual(1, len(cfg.aggregated_metrics['pretransfer_time']))


    def test_median(self):
        """ Test median computation, using a few samples """
        result = median([0.1])
        result2 = median([1])
        self.assertEqual(0.1, result)
        self.assertEqual(1, result2)

        # Test multiple eelments
        result = median([0.1, 0.2, 0.3])
        self.assertEqual(0.2, result)

        # Test averages of 2 values, with different orderings
        result = median([0.1, 0.2, 0.2, 0.3])
        result2 = median([0.2, 0.3, 0.2, 0.1])
        self.assertTrue(math.fabs(result - 0.2) < 0.001)
        self.assertTrue(math.fabs(result2 - 0.2) < 0.001)

        # Test averages of integers
        result = median([1, 2, 3, 4])
        self.assertTrue(math.fabs(float(result) - 2.5) < 0.001)


    def test_std_deviation(self):
        """ Test std deviation computation """
        result = std_deviation([2, 4, 4, 4, 5, 5, 7, 9])
        self.assertTrue(math.fabs(result - 2.0) < 0.001)

        # Test shuffled
        result2 = std_deviation([9, 4, 5, 4, 5, 4, 7, 2])
        self.assertTrue(math.fabs(float(result) - float(result2)) < 0.001)

        # Test single value
        result = std_deviation([1])
        self.assertTrue(math.fabs(float(result) - 0.0) < 0.001)

    def test_harmonic_mean(self):
        """ Test harmonic mean computation """
        function = AGGREGATES['mean_harmonic']
        result = function([1, 100])
        self.assertTrue(math.fabs(float(result) - float(1.98019802)) < 0.001)


    def test_aggregate_computations(self):
        """ Test running all the aggregates, just to see if they error """
        array = [-1, 5, 2.245, 7]
        for function in AGGREGATES.values():
            value = function(array)
            self.assertTrue(isinstance(value, int) or isinstance(value, float))


    def test_add_metric(self):
        """ Test the add-metric method for benchmarks """
        benchmark_config = Benchmark()
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


if __name__ == '__main__':
    unittest.main()