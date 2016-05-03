# Contains all the framework-general items for macros
# This allows it to be separated from resttest.py 
# This way macros (test/benchmark/etc) can import shared methods
# Without creating circular import loops

# This is all our general execution framework stuff + HTTP request stuff

import sys
import json
from email import message_from_string  # For headers handling

from .generators import parse_generator
from .parsing import *

ESCAPE_DECODING = 'string-escape'
# Python 2/3 switches
if sys.version_info[0] > 2:
    ESCAPE_DECODING = 'unicode_escape'

DEFAULT_TIMEOUT = 10  # Seconds, FIXME remove from the tests class and move to here
HEADER_ENCODING ='ISO-8859-1' # Per RFC 2616

def resolve_option(name, object_self, testset_config, cmdline_args):
    """ Look for a specific field name in a set of objects
        return value if found, return none if not found """
    for i in (object_self, testset_config, cmdline_args):
        v = gettattr(i, name, None)
        if v is not None:
            return v
    return None

class MacroCallbacks(object):  # Possibly call this an execution context?
    """ Callbacks bundle to handle reporting """

    def simple_print(self, x):
        if x: 
            print(x)

    # Called at the begining and end of the test suite
    def start_testset(self, input): lambda x: simple_print(x)
    def end_testset(self, input): lambda x: simple_print(x)
    
    # Logging outputs, these are part of the lifecycle    
    def start_macro(self, input): lambda x: simple_print(x)
    def pre_request(self, input): lambda x: simple_print(x)  # Called just before submitting requests
    def post_request(self, input): lambda x: simple_print(x) # Called just after submitting requests
    def end_macro(self, input): lambda x: simple_print(x)
    
    # These can be called at any point, theoretically
    def log_success(self, input): lambda x: simple_print(x)
    def log_failure(self, input): lambda x: simple_print(x)
    def log_status(self, input): lambda x: simple_print(x)  # Logs status info
    def log_intermediate(self, input): lambda x: simple_print(x)  # Logs debug results while running

class TestSetConfig(object):
    """ Configuration shared across all tests in a testset """
    timeout = DEFAULT_TIMEOUT  # timeout of tests, in seconds
    print_bodies = False  # Print response bodies in all cases
    print_headers = False  # Print response bodies in all cases
    retries = 0  # Retries on failures
    test_parallel = False  # Allow parallel execution of tests in a test set, for speed?
    interactive = False
    verbose = False
    ssl_insecure = False
    skip_term_colors = False  # Turn off output term colors
    junit = False # Write junit output
    junit_path = None # Path to write junit file
    working_directory = None # Working directory
    name = '' # TestSetName

    # Binding and creation of generators
    variable_binds = None
    generators = None  # Map of generator name to generator function

    def __str__(self):
        return json.dumps(self, default=safe_to_json)

class TestSet(object):
    """ Encapsulates a set of tests/benchmarks and test configuration for them 
        This is analogous to a unittest TestSuite
    """
    tests = list()
    benchmarks = list()
    config = TestSetConfig()

    def __init__(self):
        self.config = TestSetConfig()
        self.tests = list()
        self.benchmarks = list()

    def __str__(self):
        return json.dumps(self, default=safe_to_json)

class Macro(object):
    """ Common functionality used by tests, benchmarks, etc 
        Maps to a unittest TestCase, but only roughly
        This is the parent class of a Test/Benchmark/etc
    """

    name = u'Unnamed'
    macro_name = None

    def execute_macro(self, testset_config=TestSetConfig(), context=None, cmdline_args=None, callbacks=MacroCallbacks(), curl_handle=None, *args, **kwargs):
        """ Skeletal execution basis """

        callbacks.start_macro(self.name)
        callbacks.pre_request('Pre-request: no request to run')
        callbacks.post_request('Post-request: no request to run')
        callbacks.log_success('Empty macro always succeeds')
        callbacks.end_macro(self.name)

    def is_context_modifier(self):
        """ If a macro does not modify the context, it can be executed in parallel """
        return False

    def is_dynamic(self):
        """ Does the test use variables to template fields? If not, it can be executed with no templats """
        return False

    @staticmethod
    def parse(config, *args, **kwargs):  # TODO Wire me into testset parsing
        """ Parses the supplied config object from YAML, using arguments and return configured instance """
        return None

class BenchmarkResult(object):
    """ Stores results from a benchmark for reporting use """
    group = None
    name = u'unnamed'

    results = dict()  # Benchmark output, map the metric to the result array for that metric
    aggregates = list()  # List of aggregates, as tuples of (metricname, aggregate, result)
    failures = 0  # Track call count that failed

    def __init__(self):
        self.aggregates = list()
        self.results = list()

    def __str__(self):
        return json.dumps(self, default=safe_to_json)


class TestResponse(object):
    """ Encapsulates everything about a test response """
    test = None  # Test run
    response_code = None

    body = None  # Response body, if tracked

    passed = False
    response_headers = None
    failures = None

    def __init__(self):
        self.failures = list()

    def __str__(self):
        return json.dumps(self, default=safe_to_json)

def parse_headers(header_string):
    """ Parse a header-string into individual headers
        Implementation based on: http://stackoverflow.com/a/5955949/95122
        Note that headers are a list of (key, value) since duplicate headers are allowed

        NEW NOTE: keys & values are unicode strings, but can only contain ISO-8859-1 characters
    """
    # First line is request line, strip it out
    if not header_string:
        return list()
    request, headers = header_string.split('\r\n', 1)
    if not headers:
        return list()

    # Python 2.6 message header parsing fails for Unicode strings, 2.7 is fine. Go figure.
    if sys.version_info < (2,7):
        header_msg = message_from_string(headers.encode(HEADER_ENCODING))
        return [(text_type(k.lower(), HEADER_ENCODING), text_type(v, HEADER_ENCODING))
            for k, v in header_msg.items()]
    else:
        header_msg = message_from_string(headers)
        # Note: HTTP headers are *case-insensitive* per RFC 2616
        return [(k.lower(), v) for k, v in header_msg.items()]

def parse_configuration(node, base_config=None):
    """ Parse input config to configuration information """
    testset_config = base_config
    if not testset_config:
        testset_config = TestSetConfig()

    node = lowercase_keys(flatten_dictionaries(node))  # Make it usable

    for key, value in node.items():
        if key == u'timeout':
            testset_config.timeout = int(value)
        elif key == u'print_bodies':
            testset_config.print_bodies = safe_to_bool(value)
        elif key == u'retries':
            testset_config.retries = int(value)
        elif key == u'variable_binds':
            if not testset_config.variable_binds:
                testset_config.variable_binds = dict()
            testset_config.variable_binds.update(flatten_dictionaries(value))
        elif key == u'generators':
            flat = flatten_dictionaries(value)
            gen_map = dict()
            for generator_name, generator_config in flat.items():
                gen = parse_generator(generator_config)
                gen_map[str(generator_name)] = gen
            testset_config.generators = gen_map
        elif key == u'testset':
            testset_config.name = str(value)            

    return testset_config
