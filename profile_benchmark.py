# Profile the basic test execution

from pyresttest import resttest
from pyresttest.benchmarks import Benchmark
import cProfile

test = Benchmark()
test.warmup_runs = 0
test.benchmark_runs = 1000
test.raw_metrics = set()
test.metrics = {'total_time'}
test.aggregated_metrics = {'total_time': ['total','mean']}
test.url = 'http://localhost:8000/api/person/'
test.name = 'Basic GET'

cProfile.run('resttest.run_benchmark(test)', sort='cumtime')

