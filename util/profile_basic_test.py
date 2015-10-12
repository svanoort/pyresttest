from pyresttest import resttest
from pyresttest.benchmarks import Benchmark
from pyresttest.binding import Context
from pyresttest.contenthandling import ContentHandler
from pyresttest.generators import factory_generate_ids

import cProfile

cProfile.run(
    'resttest.command_line_run(["http://localhost:8000","../pyresttest/content-test.yaml"])', sort='tottime')
#cProfile.run('resttest.command_line_run(["http://localhost:8000","../examples/schema_test.yaml"])', sort='tottime')
#cProfile.run('resttest.command_line_run(["https://api.github.com","../examples/github_api_test.yaml"])', sort='tottime')
