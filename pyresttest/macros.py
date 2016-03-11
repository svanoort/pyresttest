import sys
from email import message_from_string  # For headers handling

from .generators import parse_generator
from .parsing import *

# Contains all the framework-general items for macros
# This allows it to be separated from resttest.py 
# This way macros (test/benchmark/etc) can import shared methods
# Without creating circular import loops

# This is all our general execution framework stuff + HTTP request stuff

ESCAPE_DECODING = 'string-escape'
DEFAULT_TIMEOUT = 10  # Seconds, FIXME remove from the tests class and move to here
HEADER_ENCODING ='ISO-8859-1' # Per RFC 2616

def resolve_option(name, object_self, test_config, cmdline_args):
    """ Look for a specific field name in a set of objects
        return value if found, return none if not found """
    for i in (object_self, test_config, cmdline_args):
        v = gettattr(i, name, None)
        if v is not None:
            return v
    return None

class MacroCallbacks(object):  # Possibly call this an execution context?
    """ Callbacks bundle to handle reporting """

    # Logging outputs
    def start_macro(self, input): lambda x: None
    def end_macro(self, input): lambda x: None
    def pre_request(self, input): lambda x: None  # Called just before submitting requests
    def post_request(self, input): lambda x: None # Called just after submitting requests
    def log_status(self, input): lambda x: None  # Logs status info
    def log_intermediate(self, input): lambda x: None  # Logs debug results while running

class TestConfig(object):
    """ Configuration for a test run """
    timeout = DEFAULT_TIMEOUT  # timeout of tests, in seconds
    print_bodies = False  # Print response bodies in all cases
    print_headers = False  # Print response bodies in all cases
    retries = 0  # Retries on failures
    test_parallel = False  # Allow parallel execution of tests in a test set, for speed?
    interactive = False
    verbose = False
    ssl_insecure = False
    skip_term_colors = False  # Turn off output term colors

    # Binding and creation of generators
    variable_binds = None
    generators = None  # Map of generator name to generator function

    def __str__(self):
        return json.dumps(self, default=safe_to_json)

class TestSet(object):
    """ Encapsulates a set of tests and test configuration for them """
    tests = list()
    benchmarks = list()
    config = TestConfig()

    def __init__(self):
        self.config = TestConfig()
        self.tests = list()
        self.benchmarks = list()

    def __str__(self):
        return json.dumps(self, default=safe_to_json)


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
    test_config = base_config
    if not test_config:
        test_config = TestConfig()

    node = lowercase_keys(flatten_dictionaries(node))  # Make it usable

    for key, value in node.items():
        if key == u'timeout':
            test_config.timeout = int(value)
        elif key == u'print_bodies':
            test_config.print_bodies = safe_to_bool(value)
        elif key == u'retries':
            test_config.retries = int(value)
        elif key == u'variable_binds':
            if not test_config.variable_binds:
                test_config.variable_binds = dict()
            test_config.variable_binds.update(flatten_dictionaries(value))
        elif key == u'generators':
            flat = flatten_dictionaries(value)
            gen_map = dict()
            for generator_name, generator_config in flat.items():
                gen = parse_generator(generator_config)
                gen_map[str(generator_name)] = gen
            test_config.generators = gen_map

    return test_config