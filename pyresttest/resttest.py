#!/usr/bin/env python
import sys
import os
import inspect
import traceback
import yaml
import pycurl
import json
import csv
import logging
import time

try:
    from cStringIO import StringIO as MyIO
except:
    try:
        from StringIO import StringIO as MyIO
    except ImportError:
        from io import BytesIO as MyIO

# Python 3 compatibility
if sys.version_info[0] > 2:
    from past.builtins import basestring
    from builtins import range as xrange
    ESCAPE_DECODING = 'unicode_escape'

# Dirty hack to allow for running this as a script :-/
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(
    os.path.realpath(__file__))))
    from pyresttest.six import text_type
    from pyresttest.binding import Context
    from pyresttest import generators
    from pyresttest import validators
    from pyresttest import tests
    from pyresttest.parsing import *

    from pyresttest.validators import Failure
    from pyresttest.tests import Test, DEFAULT_TIMEOUT
    from pyresttest.benchmarks import Benchmark, AGGREGATES, METRICS, parse_benchmark
    from pyresttest.macros import *
else:  # Normal imports
    from . import six
    from .six import text_type

    # Pyresttest internals
    from . import binding
    from .binding import Context
    from . import generators
    from . import parsing
    from .parsing import *
    from . import validators
    from .validators import Failure
    from . import tests
    from .tests import Test, DEFAULT_TIMEOUT
    from . import benchmarks
    from .benchmarks import Benchmark, AGGREGATES, METRICS, parse_benchmark
    from . import macros
    from .macros import *

"""
Executable class, ties everything together into the framework.
Module responsibilities:
- Read & import test test_files
- Parse test configs
- Provide executor methods for sets of tests and benchmarks
- Collect and report on test/benchmark results
- Perform analysis on benchmark results
"""
LOGGING_LEVELS = {'debug': logging.DEBUG,
                  'info': logging.INFO,
                  'warning': logging.WARNING,
                  'error': logging.ERROR,
                  'critical': logging.CRITICAL}

logging.basicConfig(format='%(levelname)s:%(message)s')
logger = logging.getLogger('pyresttest')


class cd:
    """Context manager for changing the current working directory"""
    # http://stackoverflow.com/questions/431684/how-do-i-cd-in-python/13197763#13197763

    def __init__(self, newPath):
        self.newPath = newPath

    def __enter__(self):
        if self.newPath:  # Don't CD to nothingness
            self.savedPath = os.getcwd()
            os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        if self.newPath:  # Don't CD to nothingness
            os.chdir(self.savedPath)

def read_test_file(path):
    """ Read test file at 'path' in YAML """
    # TODO allow use of safe_load_all to handle multiple test sets in a given
    # doc
    teststruct = yaml.safe_load(read_file(path))
    return teststruct


def parse_testsets(base_url, test_structure, test_files=set(), working_directory=None, vars=None):
    """ Convert a Python data structure read from validated YAML to a set of structured testsets
    The data structure is assumed to be a list of dictionaries, each of which describes:
        - a tests (test structure)
        - a simple test (just a URL, and a minimal test is created)
        - or overall test configuration for this testset
        - an import (load another set of tests into this one, from a separate file)
            - For imports, these are recursive, and will use the parent config if none is present

    Note: test_files is used to track tests that import other tests, to avoid recursive loops

    This returns a list of testsets, corresponding to imported testsets and in-line multi-document sets
    """

    tests_out = list()
    test_config = TestConfig()
    testsets = list()
    benchmarks = list()

    if working_directory is None:
        working_directory = os.path.abspath(os.getcwd())

    if vars and isinstance(vars, dict):
        test_config.variable_binds = vars

    # returns a testconfig and collection of tests
    for node in test_structure:  # Iterate through lists of test and configuration elements
        if isinstance(node, dict):  # Each config element is a miniature key-value dictionary
            node = lowercase_keys(node)
            for key in node:
                if key == u'import':
                    importfile = node[key]  # import another file
                    if importfile not in test_files:
                        logger.debug("Importing test sets: " + importfile)
                        test_files.add(importfile)
                        import_test_structure = read_test_file(importfile)
                        with cd(os.path.dirname(os.path.realpath(importfile))):
                            import_testsets = parse_testsets(
                                base_url, import_test_structure, test_files, vars=vars)
                            testsets.extend(import_testsets)
                elif key == u'url':  # Simple test, just a GET to a URL
                    mytest = Test()
                    val = node[key]
                    assert isinstance(val, basestring)
                    mytest.url = base_url + val
                    tests_out.append(mytest)
                elif key == u'test':  # Complex test with additional parameters
                    with cd(working_directory):
                        child = node[key]
                        mytest = Test.parse_test(base_url, child)
                        tests_out.append(mytest)
                elif key == u'benchmark':
                    benchmark = parse_benchmark(base_url, node[key])
                    benchmarks.append(benchmark)
                elif key == u'config' or key == u'configuration':
                    test_config = parse_configuration(
                        node[key], base_config=test_config)
    testset = TestSet()
    testset.tests = tests_out
    testset.config = test_config
    testset.benchmarks = benchmarks
    testsets.append(testset)
    return testsets

def read_file(path):
    """ Read an input into a file, doing necessary conversions around relative path handling """
    with open(path, "r") as f:
        string = f.read()
        f.close()
    return string

def log_failure(failure, context=None, test_config=TestConfig()):
    """ Log a failure from a test """
    logger.error("Test Failure, failure type: {0}, Reason: {1}".format(
        failure.failure_type, failure.message))
    if failure.details:
        logger.error("Validator/Error details:" + str(failure.details))

class LoggerCallbacks(MacroCallbacks):
    """ Uses a standard python logger """
    def log_status(self, input):
        logger.info(input)
    def log_intermediate(self, input): 
        logger.debug(input)

def run_testsets(testsets):
    """ Execute a set of tests, using given TestSet list input """
    group_results = dict()  # results, by group
    group_failure_counts = dict()
    total_failures = 0
    myinteractive = False
    curl_handle = pycurl.Curl()
    
    # Invoked during macro execution to report results
    # FIXME  I need to set up for logging before/after/during requests
    callbacks = LoggerCallbacks()

    for testset in testsets:
        mytests = testset.tests
        myconfig = testset.config
        mybenchmarks = testset.benchmarks
        context = Context()

        # Bind variables & add generators if pertinent
        if myconfig.variable_binds:
            context.bind_variables(myconfig.variable_binds)
        if myconfig.generators:
            for key, value in myconfig.generators.items():
                context.add_generator(key, value)

        # Make sure we actually have tests to execute
        if not mytests and not mybenchmarks:
            # no tests in this test set, probably just imports.. skip to next
            # test set
            break

        myinteractive = True if myinteractive or myconfig.interactive else False

        # Run tests, collecting statistics as needed
        for test in mytests:
            # Initialize the dictionaries to store test fail counts and results
            if test.group not in group_results:
                group_results[test.group] = list()
                group_failure_counts[test.group] = 0

            result = test.execute_macro(test_config=myconfig, context=context, curl_handle=curl_handle)
            result.body = None  # Remove the body, save some memory!

            if not result.passed:  # Print failure, increase failure counts for that test group
                # Use result test URL to allow for templating
                logger.error('Test Failed: ' + test.name + " URL=" + result.test.url +
                             " Group=" + test.group + " HTTP Status Code: " + str(result.response_code))

                # Print test failure reasons
                if result.failures:
                    for failure in result.failures:
                        log_failure(failure, context=context,
                                    test_config=myconfig)

                # Increment test failure counts for that group (adding an entry
                # if not present)
                failures = group_failure_counts[test.group]
                failures = failures + 1
                group_failure_counts[test.group] = failures

            else:  # Test passed, print results
                logger.info('Test Succeeded: ' + test.name +
                            " URL=" + test.url + " Group=" + test.group)

            # Add results for this test group to the resultset
            group_results[test.group].append(result)

            # handle stop_on_failure flag
            if not result.passed and test.stop_on_failure is not None and test.stop_on_failure:
                print(
                    'STOP ON FAILURE! stopping test set execution, continuing with other test sets')
                break

        for benchmark in mybenchmarks:  # Run benchmarks, analyze, write
            if not benchmark.metrics:
                logger.debug('Skipping benchmark, no metrics to collect')
                continue

            logger.info("Benchmark Starting: " + benchmark.name +
                        " Group: " + benchmark.group)
            benchmark_result = benchmark.execute_macro(test_config=myconfig, context=context)
            print(benchmark_result)
            logger.info("Benchmark Done: " + benchmark.name +
                        " Group: " + benchmark.group)

            if benchmark.output_file:  # Write file
                logger.debug(
                    'Writing benchmark to file in format: ' + benchmark.output_format)
                write_method = OUTPUT_METHODS[benchmark.output_format]
                my_file = open(benchmark.output_file, 'w')  # Overwrites file
                logger.debug("Benchmark writing to file: " +
                             benchmark.output_file)
                write_method(my_file, benchmark_result,
                             benchmark, test_config=myconfig)
                my_file.close()

    if myinteractive:
        # a break for when interactive bits are complete, before summary data
        print("===================================")

    # Print summary results
    for group in sorted(group_results.keys()):
        test_count = len(group_results[group])
        failures = group_failure_counts[group]
        total_failures = total_failures + failures

        passfail = {True: u'SUCCEEDED: ', False: u'FAILED: '}
        output_string = "Test Group {0} {1}: {2}/{3} Tests Passed!".format(group, passfail[failures == 0], str(test_count - failures), str(test_count)) 
        
        if myconfig.skip_term_colors:
            print(output_string)    
        else:
            if failures > 0:
                print('\033[91m' + output_string + '\033[0m')
            else:
                print('\033[92m' + output_string + '\033[0m')

    return total_failures


def register_extensions(modules):
    """ Import the modules and register their respective extensions """
    if isinstance(modules, basestring):  # Catch supplying just a string arg
        modules = [modules]
    for ext in modules:
        # Get the package prefix and final module name
        segments = ext.split('.')
        module = segments.pop()
        package = '.'.join(segments)
        # Necessary to get the root module back
        module = __import__(ext, globals(), locals(), package)

        # Extensions are registered by applying a register function to sets of
        # registry name/function pairs inside an object
        extension_applies = {
            'VALIDATORS': validators.register_validator,
            'COMPARATORS': validators.register_comparator,
            'VALIDATOR_TESTS': validators.register_test,
            'EXTRACTORS': validators.register_extractor,
            'GENERATORS': generators.register_generator
        }

        has_registry = False
        for registry_name, register_function in extension_applies.items():
            if hasattr(module, registry_name):
                registry = getattr(module, registry_name)
                for key, val in registry.items():
                    register_function(key, val)
                if registry:
                    has_registry = True

        if not has_registry:
            raise ImportError(
                "Extension to register did not contain any registries: {0}".format(ext))

# AUTOIMPORTS, these should run just before the main method, to ensure
# everything else is loaded
try:
    import jsonschema
    register_extensions('pyresttest.ext.validator_jsonschema')
except ImportError as ie:
    logging.debug(
        "Failed to load jsonschema validator, make sure the jsonschema module is installed if you wish to use schema validators.")

try:
    import jmespath
    register_extensions('pyresttest.ext.extractor_jmespath')
except ImportError as ie:
    logging.debug(
        "Failed to load jmespath extractor, make sure the jmespath module is installed if you wish to use jmespath extractor.")

def main(args):
    """
    Execute a test against the given base url.

    Keys allowed for args:
        url           - REQUIRED - Base URL
        test          - REQUIRED - Test file (yaml)
        print_bodies  - OPTIONAL - print response body
        print_headers  - OPTIONAL - print response headers
        log           - OPTIONAL - set logging level {debug,info,warning,error,critical} (default=warning)
        interactive   - OPTIONAL - mode that prints info before and after test exectuion and pauses for user input for each test
        absolute_urls - OPTIONAL - mode that treats URLs in tests as absolute/full URLs instead of relative URLs
        skip_term_colors - OPTIONAL - mode that turn off the output term colors
    """

    if 'log' in args and args['log'] is not None:
        logger.setLevel(LOGGING_LEVELS.get(
            args['log'].lower(), logging.NOTSET))

    if 'import_extensions' in args and args['import_extensions']:
        extensions = args['import_extensions'].split(';')

        # We need to add current folder to working path to import modules
        working_folder = args['cwd']
        if working_folder not in sys.path:
            sys.path.insert(0, working_folder)
        register_extensions(extensions)

    test_file = args['test']
    test_structure = read_test_file(test_file)

    my_vars = None
    if 'vars' in args and args['vars'] is not None:
        my_vars = yaml.safe_load(args['vars'])
    if my_vars and not isinstance(my_vars, dict):
        raise Exception("Variables must be a dictionary!")

    # Set up base URL
    base_url = args['url']

    if 'absolute_urls' in args and args['absolute_urls']:
        base_url = ''

    tests = parse_testsets(base_url, test_structure,
                           working_directory=os.path.dirname(test_file), vars=my_vars)

    # Override configs from command line if config set
    for t in tests:
        if 'print_bodies' in args and args['print_bodies'] is not None and bool(args['print_bodies']):
            t.config.print_bodies = safe_to_bool(args['print_bodies'])

        if 'print_headers' in args and args['print_headers'] is not None and bool(args['print_headers']):
            t.config.print_headers = safe_to_bool(args['print_headers'])

        if 'interactive' in args and args['interactive'] is not None:
            t.config.interactive = safe_to_bool(args['interactive'])

        if 'verbose' in args and args['verbose'] is not None:
            t.config.verbose = safe_to_bool(args['verbose'])

        if 'ssl_insecure' in args and args['ssl_insecure'] is not None:
            t.config.ssl_insecure = safe_to_bool(args['ssl_insecure'])

        if 'skip_term_colors' in args and args['skip_term_colors'] is not None:
            t.config.skip_term_colors = safe_to_bool(args['skip_term_colors'])

    # Execute all testsets
    failures = run_testsets(tests)

    sys.exit(failures)


def command_line_run(args_in):
    args = parse_command_line_args(args_in)
    main(args)

# Allow import into another module without executing the main method
if(__name__ == '__main__'):
    command_line_run(sys.argv[1:])
