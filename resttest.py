import sys
import os
import math
import operator
import argparse
import yaml
import pycurl
import json
import csv
import StringIO
import logging

LOGGING_LEVELS = {'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL}

#Map HTTP method names to curl methods
#Kind of obnoxious that it works this way...
HTTP_METHODS = {u'GET' : pycurl.HTTPGET,
    u'PUT' : pycurl.UPLOAD,
    u'POST' : pycurl.POST,
    u'DELETE'  : 'DELETE'}

#Curl metrics for benchmarking, key is name in config file, value is pycurl variable
#Taken from pycurl docs, this is libcurl variable minus the CURLINFO prefix
# Descriptions of the timing variables are taken from libcurl docs:
#   http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html

METRICS = {
    #Timing info, precisely in order from start to finish
    #The time it took from the start until the name resolving was completed.
    'namelookup_time' : pycurl.NAMELOOKUP_TIME,

    #The time it took from the start until the connect to the remote host (or proxy) was completed.
    'connect_time' : pycurl.CONNECT_TIME,

    #The time it took from the start until the SSL connect/handshake with the remote host was completed.
    'appconnect_time' : pycurl.APPCONNECT_TIME,

    #The time it took from the start until the file transfer is just about to begin.
    #This includes all pre-transfer commands and negotiations that are specific to the particular protocol(s) involved.
    'pretransfer_time' : pycurl.PRETRANSFER_TIME,

    #The time it took from the start until the first byte is received by libcurl.
    'starttransfer_time' : pycurl.STARTTRANSFER_TIME,

    #The time it took for all redirection steps include name lookup, connect, pretransfer and transfer
    #  before final transaction was started. So, this is zero if no redirection took place.
    'redirect_time' : pycurl.REDIRECT_TIME,

    #Total time of the previous request.
    'total_time' : pycurl.TOTAL_TIME,


    #Transfer sizes and speeds
    'size_download' : pycurl.SIZE_DOWNLOAD,
    'size_upload' : pycurl.SIZE_UPLOAD,
    'request_size' : pycurl.REQUEST_SIZE,
    'speed_download' : pycurl.SPEED_DOWNLOAD,
    'speed_upload' : pycurl.SPEED_UPLOAD,

    #Connection counts
    'redirect_count' : pycurl.REDIRECT_COUNT,
    'num_connects' : pycurl.NUM_CONNECTS
}

#Map statistical aggregate to the function to use to perform the aggregation on an array
AGGREGATES = {
    'mean_arithmetic': #AKA the average, good for many things
        lambda x: float(sum(x))/float(len(x)),
    'mean':  # Alias for arithmetic mean
        lambda x: float(sum(x))/float(len(x)),
    'mean_harmonic': #Harmonic mean, better predicts average of rates: http://en.wikipedia.org/wiki/Harmonic_mean
        lambda x: 1.0/( sum([1.0/float(y) for y in x]) / float(len(x))),
    'median':  lambda x: median(x),
    'std_deviation': lambda x: std_deviation(x)
}

def median(array):
    """ Get the median of an array """
    sorted = [x for x in array]
    sorted.sort()
    middle = len(sorted)/2 #Gets the middle element, if present
    if len(sorted) % 2 == 0: #Even, so need to average together the middle two values
        return float((sorted[middle]+sorted[middle-1]))/2
    else:
        return sorted[middle]

def std_deviation(array):
    """ Compute the standard deviation of an array of numbers """
    if not array or len(array) == 1:
        return 0

    average = AGGREGATES['mean_arithmetic'](array)
    variance = map(lambda x: (x-average)**2,array)
    stdev = AGGREGATES['mean_arithmetic'](variance)
    return math.sqrt(stdev)

class cd:
    """Context manager for changing the current working directory"""
    # http://stackoverflow.com/questions/431684/how-do-i-cd-in-python/13197763#13197763

    def __init__(self, newPath):
        self.newPath = newPath

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

class BodyReader:
    ''' Read from a data str/byte array into reader function for pyCurl '''

    def __init__(self, data):
        self.data = data
        self.loc = 0

    def readfunction(self, size):
        startidx = self.loc
        endidx = startidx + size
        data = self.data

        if data is None or len(data) == 0:
            return ''

        if endidx >= len(data):
            endidx = len(data) - 1

        result = data[startidx : endidx]
        self.loc += (endidx-startidx)
        return result

class Test(object):
    """ Describes a REST test """
    url  = None
    expected_status = [200]  # expected HTTP status code or codes
    body = None #Request body, if any (for POST/PUT methods)
    headers = dict() #HTTP Headers
    method = u'GET'
    group = u'Default'
    name = u'Unnamed'
    validators = None  # Validators for response body, IE regexes, etc
    stop_on_failure = False
    #In this case, config would be used by all tests following config definition, and in the same scope as tests

    def __init__(self):
        self.headers = dict()
        self.expected_status = [200]

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class Validator:
    """ Validation for a dictionary """
    query = None
    expected = None
    operator = "eq"
    passed = None
    actual = None
    query_delimiter = "/"
    export_as = None

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def validate(self, mydict):
        """ Uses the query as an XPath like query to extract a value from the dict and verify result against expectation """

        if self.query is None:
            raise Exception("Validation missing attribute 'query': " + str(self))

        if not isinstance(self.query, str):
            raise Exception("Validation attribute 'query' type is not str: " + type(self.query).__name__)

        if self.operator is None:
            raise Exception("Validation missing attribute 'operator': " + str(self))

        # from http://stackoverflow.com/questions/7320319/xpath-like-query-for-nested-python-dictionaries
        self.actual = mydict
        try:
            logging.debug("Validator: pre query: " + str(self.actual))
            for x in self.query.strip(self.query_delimiter).split(self.query_delimiter):
                logging.debug("Validator: x = " + x)
                try:
                    x = int(x)
                    self.actual = self.actual[x]
                except ValueError:
                    self.actual = self.actual.get(x)
        except:
            logging.debug("Validator: exception applying query")
            pass

        # default to false, if we have a check it has to hit either count or expected checks!
        output = False

        if self.operator == "exists":
            # require actual value
            logging.debug("Validator: exists check")
            output = True if self.actual is not None else False
        elif self.operator == "empty":
            # expect no actual value
            logging.debug("Validator: empty check" )
            output = True if self.actual is None else False
        elif self.actual is None:
            # all tests beyond here require actual to be set
            logging.debug("Validator: actual is None")
            output = False
        elif self.expected is None:
            raise Exception("Validation missing attribute 'expected': " + str(self))
        elif self.operator == "count":
            self.actual = len(self.actual) # for a count, actual is the count of the collection
            logging.debug("Validator: count check")
            output = True if self.actual == self.expected else False
        else:
            logging.debug("Validator: operator check: " + str(self.expected) + " " + str(self.operator) + " " + str(self.actual))

            # any special case operators here:
            if self.operator == "contains":
                if isinstance(self.actual, dict) or isinstance(self.actual, list):
                    output = True if self.expected in self.actual else False
                else:
                    raise Exception("Attempted to use 'contains' operator on non-collection type: " + type(self.actual).__name__)
            else:
                # operator list: https://docs.python.org/2/library/operator.html
                myoperator = getattr(operator, self.operator)
                output = True if myoperator(self.actual, self.expected) == True else False

        #print "Validator: output is " + str(output)

        # if export_as is set, export to environ
        if self.export_as is not None and self.actual is not None:
            logging.debug("Validator: export " + self.export_as + " = " + str(self.actual))
            os.environ[self.export_as] = str(self.actual)

        self.passed = output

        return output

class TestConfig:
    """ Configuration for a test run """
    timeout = 10  # timeout of tests, in seconds
    print_bodies = False  # Print response bodies in all cases
    retries = 0  # Retries on failures
    test_parallel = False  # Allow parallel execution of tests in a test set, for speed?
    validator_query_delimiter = "/"
    interactive = False

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class TestSet:
    """ Encapsulates a set of tests and test configuration for them """
    tests = list()
    benchmarks = list()
    config = TestConfig()

    def __init__(self):
        self.config = TestConfig()
        self.tests = list()
        self.benchmarks = list()

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class BenchmarkResult:
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
        return json.dumps(self, default=lambda o: o.__dict__)

class Benchmark(Test):
    """ Extends test with configuration for benchmarking
        warmup_runs and benchmark_runs behave like you'd expect

        Metrics are a bit tricky:
            - Key is metric name from METRICS
            - Value is either a single value or a list:
                - list contains aggregagate name from AGGREGATES
                - value of 'all' returns everything
    """
    warmup_runs = 10 #Times call is executed to warm up
    benchmark_runs = 100 #Times call is executed to generate benchmark results
    output_format = u'csv'
    output_file = None

    #Metrics to gather, both raw and aggregated
    metrics = set()

    raw_metrics = set()  # Metrics that do not have any aggregation performed
    aggregated_metrics = dict()  # Metrics where an aggregate is computed, maps key(metric name) -> list(aggregates to use)

    def add_metric(self, metric_name, aggregate=None):
        """ Add a metric-aggregate pair to the benchmark, where metric is a number to measure from curl, and aggregate is an aggregation function
            (See METRICS and AGGREGATES)
            If aggregate is not defined (False,empty, or None), then the raw number is reported
            Returns self, for fluent-syle construction of config """

        clean_metric = metric_name.lower().strip()

        if clean_metric.lower() not in METRICS:
            raise Exception("Metric named: " + metric_name + " is not a valid benchmark metric.")
        self.metrics.add(clean_metric)

        if not aggregate:
            self.raw_metrics.add(clean_metric)
        elif aggregate.lower().strip() in AGGREGATES:
            # Add aggregate to this metric
            clean_aggregate = aggregate.lower().strip()
            current_aggregates = self.aggregated_metrics.get(clean_metric, list())
            current_aggregates.append(clean_aggregate)
            self.aggregated_metrics[clean_metric]  = current_aggregates
        else:
            raise Exception("Aggregate function " + aggregate + " is not a legal aggregate function name");

        return self;


    def __init__(self):
        self.metrics = set()
        self.raw_metrics = set()
        self.aggregated_metrics = dict()
        super(Benchmark, self).__init__()

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

class TestResponse:
    """ Encapsulates everything about a test response """
    test = None #Test run
    response_code = None
    body = bytearray() #Response body, if tracked
    passed = False
    response_headers = bytearray()

    def __str__(self):
        return json.dumps(self, default=lambda o: str(o) if isinstance(o, bytearray) else o.__dict__)

    def body_callback(self, buf):
        """ Write response body by pyCurl callback """
        self.body.extend(buf)

    def unicode_body(self):
        return unicode(self.body.decode('UTF-8'))

    def header_callback(self,buf):
        """ Write headers by pyCurl callback """
        self.response_headers.extend(buf) #Optional TODO use chunk or byte-array storage

def read_test_file(path):
    """ Read test file at 'path' in YAML """
    #TODO Handle multiple test sets in a given doc
    teststruct = yaml.safe_load(os.path.expandvars(read_file(path)))
    return teststruct

def build_testsets(base_url, test_structure, test_files = set() ):
    """ Convert a Python datastructure read from validated YAML to a set of structured testsets
    The data stucture is assumed to be a list of dictionaries, each of which describes:
        - a tests (test structure)
        - a simple test (just a URL, and a minimal test is created)
        - or overall test configuration for this testset
        - an import (load another set of tests into this one, from a separate file)
            - For imports, these are recursive, and will use the parent config if none is present

    Note: test_files is used to track tests that import other tests, to avoid recursive loops

    This returns a list of testsets, corresponding to imported testsets and in-line multi-document sets

    TODO: Implement imports (with test_config handled) and import of multi-document YAML """

    tests_out = list()
    test_config = TestConfig()
    testsets = list()
    benchmarks = list()
    #returns a testconfig and collection of tests
    for node in test_structure: #Iterate through lists of test and configuration elements
        if isinstance(node,dict): #Each config element is a miniature key-value dictionary
            node = lowercase_keys(node)
            for key in node:
                if key == u'import':
                    importfile = node[key] #import another file
                    if importfile not in test_files:
                        logging.debug("Importing test sets: " + importfile)
                        test_files.add(importfile)
                        import_test_structure = read_test_file(importfile)
                        with cd(os.path.dirname(os.path.realpath(importfile))):
                            import_testsets = build_testsets(base_url, import_test_structure, test_files)
                            testsets.extend(import_testsets)
                elif key == u'url': #Simple test, just a GET to a URL
                    mytest = Test()
                    val = node[key]
                    assert isinstance(val,str) or isinstance(val,unicode)
                    mytest.url = base_url + val
                    tests_out.append(mytest)
                elif key == u'test': #Complex test with additional parameters
                    child = node[key]
                    mytest = build_test(base_url, child)
                    tests_out.append(mytest)
                elif key == u'benchmark':
                    benchmark = build_benchmark(base_url, node[key])
                    benchmarks.append(benchmark)
                elif key == u'config' or key == u'configuration':
                    test_config = make_configuration(node[key])
    testset = TestSet()
    testset.tests = tests_out
    testset.config = test_config
    testset.benchmarks = benchmarks
    testsets.append(testset)
    return testsets

def safe_to_bool(input):
    """ Safely convert user input to a boolean, throwing exception if not boolean or boolean-appropriate string
      For flexibility, we allow case insensitive string matching to false/true values
      If it's not a boolean or string that matches 'false' or 'true' when ignoring case, throws an exception """
    if isinstance(input,bool):
        return input
    elif isinstance(input,unicode) or isinstance(input,str) and unicode(input,'UTF-8').lower() == u'false':
        return False
    elif isinstance(input,unicode) or isinstance(input,str) and unicode(input,'UTF-8').lower() == u'true':
        return True
    else:
        raise TypeError('Input Object is not a boolean or string form of boolean!')


def make_configuration(node):
    """ Convert input object to configuration information """
    test_config = TestConfig()

    node = lowercase_keys(flatten_dictionaries(node))  # Make it usable

    for key, value in node.items():
        if key == u'timeout':
            test_config.timeout = int(value)
        elif key == u'print_bodies':
            test_config.print_bodies = safe_to_bool(value)
        elif key == u'retries':
            test_config.retries = int(value)
        elif key == u'validator_query_delimiter':
            test_config.validator_query_delimiter = str(value)

    return test_config

def flatten_dictionaries(input):
    """ Flatten a list of dictionaries into a single dictionary, to allow flexible YAML use
      Dictionary comprehensions can do this, but would like to allow for pre-Python 2.7 use
      If input isn't a list, just return it.... """
    output = dict()
    if isinstance(input, list):
        for map in input:
            if not isinstance(map, dict):
                raise Exception('Tried to flatten a list of NON-dictionaries into a single dictionary. Whoops!')
            for key in map.keys(): #Add keys into output
                output[key]=map[key]
    else: #Not a list of dictionaries
        output = input;
    return output

def lowercase_keys(input_dict):
    """ Take input and if a dictionary, return version with keys all lowercase """
    if not isinstance(input_dict,dict):
        return input_dict

    safe = dict()
    for key,value in input_dict.items():
        safe[str(key).lower()] = value
    return safe


def read_file(path): #TODO implementme, handling paths more intelligently
    """ Read an input into a file, doing necessary conversions around relative path handling """
    f = open(path, "r")
    string = f.read()
    f.close()
    return string

def build_test(base_url, node, input_test = None):
    """ Create or modify a test, input_test, using configuration in node, and base_url
     If no input_test is given, creates a new one

     Uses explicitly specified elements from the test input structure
     to make life *extra* fun, we need to handle list <-- > dict transformations.

     This is to say: list(dict(),dict()) or dict(key,value) -->  dict() for some elements

     Accepted structure must be a single dictionary of key-value pairs for test configuration """

    mytest = input_test
    if not mytest:
        mytest = Test()

    node = lowercase_keys(flatten_dictionaries(node)) #Clean up for easy parsing

    #Copy/convert input elements into appropriate form for a test object
    for configelement, configvalue in node.items():
        #Configure test using configuration elements
        if configelement == u'url':
            assert isinstance(configvalue,str) or isinstance(configvalue,unicode) or isinstance(configvalue,int)
            mytest.url = base_url + unicode(configvalue,'UTF-8').encode('ascii','ignore')
        elif configelement == u'method': #Http method, converted to uppercase string
            var = unicode(configvalue,'UTF-8').upper()
            assert var in HTTP_METHODS
            mytest.method = var
        elif configelement == u'group': #Test group
            assert isinstance(configvalue,str) or isinstance(configvalue,unicode) or isinstance(configvalue,int)
            mytest.group = unicode(configvalue,'UTF-8')
        elif configelement == u'name': #Test name
            assert isinstance(configvalue,str) or isinstance(configvalue,unicode) or isinstance(configvalue,int)
            mytest.name = unicode(configvalue,'UTF-8')
        elif configelement == u'validators':
            #TODO implement more validators: regex, file/schema match, etc
            if isinstance(configvalue, list):
                for var in configvalue:
                    myquery = var.get(u'query')
                    myoperator = var.get(u'operator')
                    myexpected = var.get(u'expected')
                    myexportas = var.get(u'export_as')

                    # NOTE structure is checked by use of validator, do not verify attributes here
                    # create validator and add to list of validators
                    if mytest.validators is None:
                        mytest.validators = list()
                    validator = Validator()
                    validator.query = myquery
                    validator.expected = myexpected
                    validator.operator = myoperator if myoperator is not None else validator.operator
                    validator.export_as = myexportas if myexportas is not None else validator.export_as
                    mytest.validators.append(validator)
            else:
                raise Exception('Misconfigured validator, requires type property')
        elif configelement == u'body': #Read request body, either as inline input or from file
            #Body is either {'file':'myFilePath'} or inline string with file contents
            if isinstance(configvalue, dict) and u'file' in lowercase_keys(configvalue):
                var = lowercase_keys(configvalue)
                assert isinstance(var[u'file'],str) or isinstance(var[u'file'],unicode)
                mytest.body = os.path.expandvars(read_file(var[u'file'])) #TODO change me to pass in a file handle, rather than reading all bodies into RAM
            elif isinstance(configvalue, str):
                mytest.body = configvalue
            else:
                # TODO add ability to handle input of directories or file lists with wildcards to test against multiple bodies
                raise Exception('Illegal input to HTTP request body: must be string or map of file -> path')

        elif configelement == 'headers': #HTTP headers to use, flattened to a single string-string dictionary
            mytest.headers = flatten_dictionaries(configvalue)
        elif configelement == 'expected_status': #List of accepted HTTP response codes, as integers
            expected = list()
            #If item is a single item, convert to integer and make a list of 1
            #Otherwise, assume item is a list and convert to a list of integers
            if isinstance(configvalue,list):
                for item in configvalue:
                    expected.append(int(item))
            else:
                expected.append(int(configvalue))
            mytest.expected_status = expected
        elif configelement == 'stop_on_failure':
            mytest.stop_on_failure = safe_to_bool(configvalue)

    #Next, we adjust defaults to be reasonable, if the user does not specify them

    #For non-GET requests, accept additional response codes indicating success
    # (but only if not expected statuses are not explicitly specified)
    #  this is per HTTP spec: http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.5
    if 'expected_status' not in node.keys():
        if mytest.method == 'POST':
            mytest.expected_status = [200,201,204]
        elif mytest.method == 'PUT':
            mytest.expected_status = [200,201,204]
        elif mytest.method == 'DELETE':
            mytest.expected_status = [200,202,204]

    return mytest

def build_benchmark(base_url, node):
    """ Try building a benchmark configuration from deserialized configuration root node """
    node = lowercase_keys(flatten_dictionaries(node))  # Make it usable

    benchmark = Benchmark()

    # Read & set basic test parameters
    benchmark = build_test(base_url, node, benchmark)

    # Complex parsing because of list/dictionary/singleton legal cases
    for key, value in node.items():
        if key == u'warmup_runs':
            benchmark.warmup_runs = int(value)
        elif key == u'benchmark_runs':
            benchmark.benchmark_runs = int(value)
        elif key == u'output_format':
            format = value.lower()
            if format in OUTPUT_FORMATS:
                benchmark.output_format = format
            else:
                raise Exception('Invalid benchmark output format: ' + format)
        elif key == u'output_file':
            if not isinstance(value, basestring):
                raise Exception("Invalid output file format")
            benchmark.output_file = value
        elif key == u'metrics':
            if isinstance(value, unicode) or isinstance(value,str):
                # Single value
                benchmark.add_metric(unicode(value, 'UTF-8'))
            elif isinstance(value, list) or isinstance(value, set):
            # List of single values or list of {metric:aggregate, ...}
                for metric in value:
                    if isinstance(metric, dict):
                        for metricname, aggregate in metric.items():
                            if not isinstance(metricname, basestring):
                                raise Exception("Invalid metric input: non-string metric name")
                            if not isinstance(aggregate, basestring):
                                raise Exception("Invalid aggregate input: non-string aggregate name")
                            # TODO unicode-safe this
                            benchmark.add_metric(unicode(metricname,'UTF-8'), unicode(aggregate,'UTF-8'))

                    elif isinstance(metric, unicode) or isinstance(metric, str):
                        benchmark.add_metric(unicode(metric,'UTF-8'))
            elif isinstance(value, dict):
                # Dictionary of metric-aggregate pairs
                for metricname, aggregate in value.items():
                    if not isinstance(metricname, basestring):
                        raise Exception("Invalid metric input: non-string metric name")
                    if not isinstance(aggregate, basestring):
                        raise Exception("Invalid aggregate input: non-string aggregate name")
                    benchmark.add_metric(unicode(metricname,'UTF-8'), unicode(aggregate,'UTF-8'))
            else:
                raise Exception("Invalid benchmark metric datatype: "+str(value))

    return benchmark

def configure_curl(mytest, test_config = TestConfig()):
    """ Create and mostly configure a curl object for test """

    if not isinstance(mytest, Test):
        raise Exception('Need to input a Test type object')
    if not isinstance(test_config, TestConfig):
        raise Exception('Need to input a TestConfig type object for the testconfig')

    curl = pycurl.Curl()
    # curl.setopt(pycurl.VERBOSE, 1)  # Debugging convenience
    curl.setopt(curl.URL, str(mytest.url))
    curl.setopt(curl.TIMEOUT, test_config.timeout)


    #TODO use CURLOPT_READDATA http://pycurl.sourceforge.net/doc/files.html and lazy-read files if possible

    # HACK: process env vars again, since we have an extract capabilitiy in validation.. this is a complete hack, but I need functionality over beauty
    if mytest.body is not None:
        mytest.body = os.path.expandvars(mytest.body)

    # Set read function for post/put bodies
    if mytest.method == u'POST' or mytest.method == u'PUT':
        curl.setopt(curl.READFUNCTION, StringIO.StringIO(mytest.body).read)

    if mytest.method == u'POST':
        curl.setopt(HTTP_METHODS[u'POST'], 1)
        if mytest.body is not None:
            curl.setopt(pycurl.POSTFIELDSIZE, len(mytest.body))  # Required for some servers
    elif mytest.method == u'PUT':
        curl.setopt(HTTP_METHODS[u'PUT'], 1)
        if mytest.body is not None:
            curl.setopt(pycurl.INFILESIZE, len(mytest.body))  # Required for some servers
    elif mytest.method == u'DELETE':
        curl.setopt(curl.CUSTOMREQUEST,'DELETE')

    headers = list()
    if mytest.headers: #Convert headers dictionary to list of header entries, tested and working
        for headername, headervalue in mytest.headers.items():
            headers.append(str(headername) + ': ' +str(headervalue))
    headers.append("Expect:")  # Fix for expecting 100-continue from server, which not all servers will send!
    headers.append("Connection: close")
    curl.setopt(curl.HTTPHEADER, headers)
    return curl

def run_test(mytest, test_config = TestConfig()):
    """ Put together test pieces: configure & run actual test, return results """

    curl = configure_curl(mytest, test_config)
    result = TestResponse()
    # reset the body, it holds values from previous runs otherwise
    result.body = bytearray()
    curl.setopt(pycurl.WRITEFUNCTION, result.body_callback)
    curl.setopt(pycurl.HEADERFUNCTION, result.header_callback) #Gets headers

    if test_config.interactive:
        print "==================================="
        print "%s" % mytest.name
        print "-----------------------------------"
        print "REQUEST:"
        print "%s %s" % (mytest.method, mytest.url)
        if mytest.body is not None:
            print "\n%s" % mytest.body
        raw_input("Press ENTER when ready: ")

    try:
        curl.perform() #Run the actual call
    except Exception as e:
        print e  #TODO figure out how to handle failures where no output is generated IE connection refused

    result.test = mytest
    response_code = curl.getinfo(pycurl.RESPONSE_CODE)
    result.response_code = response_code
    result.passed = response_code in mytest.expected_status
    logging.debug("Initial Test Result, based on expected response code: "+str(result.passed))

    #print str(test_config.print_bodies) + ',' + str(not result.passed) + ' , ' + str(test_config.print_bodies or not result.passed)

    #Print response body if override is set to print all *OR* if test failed (to capture maybe a stack trace)
    if test_config.print_bodies:
        if test_config.interactive:
            print "RESPONSE:"
        print result.body

    # execute validator on body
    if result.passed == True:
        if mytest.validators is not None and isinstance(mytest.validators, list):
            logging.debug("executing this many validators: " + str(len(mytest.validators)))
            myjson = json.loads(str(result.body))
            for validator in mytest.validators:
                # pass delimiter from config to validator
                validator.query_delimiter = test_config.validator_query_delimiter
                # execute validation
                mypassed = validator.validate(myjson)
                if mypassed == False:
                    result.passed = False
                    # do NOT break, collect all validation data!
                if test_config.interactive:
                    # expected isn't really required, so accomidate with prepending space if it is set, else make it empty (for formatting)
                    myexpected = " " + str(validator.expected) if validator.expected is not None else ""
                    print "VALIDATOR: " + validator.query + " " + validator.operator + myexpected + " = " + str(validator.passed)
        else:
            logging.debug("no validators found")

    logging.debug(result)

    curl.close()
    return result

def run_benchmark(curl, benchmark, test_config = TestConfig()):
    """ Perform a benchmark, (re)using a given, configured CURL call to do so
        The actual analysis of metrics is performed separately, to allow for testing
    """

    warmup_runs = benchmark.warmup_runs
    benchmark_runs = benchmark.benchmark_runs
    message = ''  #Message is name of benchmark... print it?

    if (warmup_runs <= 0):
        raise Exception("Invalid number of warmup runs, must be > 0 :" + warmup_runs)
    if (benchmark_runs <= 0):
        raise Exception("Invalid number of benchmark runs, must be > 0 :" + benchmark_runs)

    #Initialize variables to store output
    output = BenchmarkResult()
    output.name = benchmark.name
    output.group = benchmark.group
    metricnames = list(benchmark.metrics)
    metricvalues = [METRICS[name] for name in metricnames]  # Metric variable for curl, to avoid hash lookup for every metric name
    results = [list() for x in xrange(0, len(metricnames))]  # Initialize arrays to store results for each metric

    curl.setopt(pycurl.WRITEFUNCTION, lambda x: None) #Do not store actual response body at all.

    #Benchmark warm-up to allow for caching, JIT compiling, on client
    logging.info('Warmup: ' + message + ' started')
    for x in xrange(0, warmup_runs):
        if benchmark.method == u'POST' or benchmark.method == u'PUT':
            curl.setopt(curl.READFUNCTION, StringIO.StringIO(benchmark.body).read)
        curl.perform()
    logging.info('Warmup: ' + message + ' finished')

    logging.info('Benchmark: ' + message + ' starting')

    for x in xrange(0, benchmark_runs):  # Run the actual benchmarks
        if benchmark.method == u'POST' or benchmark.method == u'PUT':
            curl.setopt(curl.READFUNCTION, StringIO.StringIO(benchmark.body).read)

        try:  # Run the curl call, if it errors, then add to failure counts for benchmark
            curl.perform()
        except Exception:
            output.failures = output.failures + 1
            continue  # Skip metrics collection

        # Get all metrics values for this run, and store to metric lists
        for i in xrange(0, len(metricnames)):
            results[i].append( curl.getinfo(metricvalues[i]) )

    logging.info('Benchmark: ' + message + ' ending')

    temp_results = dict()
    for i in xrange(0, len(metricnames)):
        temp_results[metricnames[i]] = results[i]
    output.results = temp_results

    curl.close()
    return analyze_benchmark_results(output, benchmark)


def analyze_benchmark_results(benchmark_result, benchmark):
    """ Take a benchmark result containing raw benchmark results, and do aggregation by
    applying functions

    Aggregates come out in format of metricname, aggregate_name, result
    """

    output = BenchmarkResult()
    output.name = benchmark_result.name
    output.group = benchmark_result.group
    output.failures = benchmark_result.failures

    # Copy raw metric arrays over where necessary
    raw_results = benchmark_result.results
    temp = dict()
    for metric in benchmark.raw_metrics:
        temp[metric] = raw_results[metric]
    output.results = temp

    # Compute aggregates for each metric, and add tuples to aggregate results
    aggregate_results = list()
    for metricname, aggregate_list in benchmark.aggregated_metrics.iteritems():
        numbers = raw_results[metricname]
        for aggregate_name in aggregate_list:
            if numbers:  # Only compute aggregates if numbers exist
                aggregate_function = AGGREGATES[aggregate_name]
                aggregate_results.append( (metricname, aggregate_name, aggregate_function(numbers)) )
            else:
                aggregate_results.append( (metricname, aggregate_name, None) )

    output.aggregates = aggregate_results
    return output


def metrics_to_tuples(raw_metrics):
    """ Converts metric dictionary of name:values_array into list of tuples
        Use case: writing out benchmark to CSV, etc

        Input:
        {'metric':[value1,value2...], 'metric2':[value1,value2,...]...}

        Output: list, with tuple header row, then list of tuples of values
        [('metric','metric',...), (metric1_value1,metric2_value1, ...) ... ]
    """
    if not isinstance(raw_metrics, dict):
        raise TypeError("Input must be dictionary!")

    metrics = sorted(raw_metrics.keys())
    arrays = [raw_metrics[metric] for metric in metrics]

    num_rows = len(arrays[0])  # Assume all same size or this fails
    output = list()
    output.append(tuple(metrics))  # Add headers

    # Create list of tuples mimicking 2D array from input
    for row in xrange(0, num_rows):
        new_row = tuple([arrays[col][row] for col in xrange(0, len(arrays))])
        output.append(new_row)
    return output

def write_benchmark_json(file_out, benchmark_result, benchmark, test_config = TestConfig()):
    """ Writes benchmark to file as json """
    json.dump(benchmark_result, file_out, default=lambda o: o.__dict__)

def write_benchmark_csv(file_out, benchmark_result, benchmark, test_config = TestConfig()):
    """ Writes benchmark to file as csv """
    writer = csv.writer(file_out)
    writer.writerow(('Benchmark', benchmark_result.name))
    writer.writerow(('Benchmark Group', benchmark_result.group))
    writer.writerow(('Failures', benchmark_result.failures))

    # Write result arrays
    if benchmark_result.results:
        writer.writerow(('Results',''))
        writer.writerows(metrics_to_tuples(benchmark_result.results))
    if benchmark_result.aggregates:
        writer.writerow(('Aggregates',''))
        writer.writerows(benchmark_result.aggregates)

OUTPUT_FORMATS = [u'csv', u'json']

# Method to call when writing benchmark file
OUTPUT_METHODS = {u'csv' : write_benchmark_csv, u'json': write_benchmark_json}


def execute_testsets(testsets):
    """ Execute a set of tests, using given TestSet list input """
    group_results = dict() #results, by group
    group_failure_counts = dict()
    total_failures = 0
    myinteractive = False

    for testset in testsets:
        mytests = testset.tests
        myconfig = testset.config
        mybenchmarks = testset.benchmarks

        #Make sure we actually have tests to execute
        if not mytests and not mybenchmarks:
            # no tests in this test set, probably just imports.. skip to next test set
            break

        myinteractive = True if myinteractive or myconfig.interactive else False

        #Run tests, collecting statistics as needed
        for test in mytests:
            #Initialize the dictionaries to store test fail counts and results
            if test.group not in group_results:
                group_results[test.group] = list()
                group_failure_counts[test.group] = 0

            result = run_test(test, test_config = myconfig)
            result.body = None  # Remove the body, save some memory!

            if not result.passed: #Print failure, increase failure counts for that test group
                logging.error('Test Failed: '+test.name+" URL="+test.url+" Group="+test.group+" HTTP Status Code: "+str(result.response_code))

                if test.validators is not None:
                    for validator in test.validators:
                        if validator.passed == False:
                            logging.warning("   Validation Failed: " + str(validator))

                #Increment test failure counts for that group (adding an entry if not present)
                failures = group_failure_counts[test.group]
                failures = failures + 1
                group_failure_counts[test.group] = failures

            else: #Test passed, print results
                logging.info('Test Succeeded: '+test.name+" URL="+test.url+" Group="+test.group)

            #Add results for this test group to the resultset
            group_results[test.group].append(result)

            # handle stop_on_failure flag
            if not result.passed and test.stop_on_failure is not None and test.stop_on_failure:
                print 'STOP ON FAILURE! stopping test set execution, continuing with other test sets'
                break

        for benchmark in mybenchmarks:  # Run benchmarks, analyze, write
            if not benchmark.metrics:
                logging.debug('Skipping benchmark, no metrics to collect')
                continue

            logging.info("Benchmark Starting: "+benchmark.name+" Group: "+benchmark.group)
            curl = configure_curl(benchmark, myconfig)
            benchmark_result = run_benchmark(curl, benchmark, myconfig)
            print benchmark_result
            logging.info("Benchmark Done: "+benchmark.name+" Group: "+benchmark.group)

            if benchmark.output_file:  # Write file
                logging.debug('Writing benchmark to file in format: '+benchmark.output_format)
                write_method = OUTPUT_METHODS[benchmark.output_format]
                my_file =  open(benchmark.output_file, 'w')  # Overwrites file
                logging.debug("Benchmark writing to file: " + benchmark.output_file)
                write_method(my_file, benchmark_result, benchmark, test_config = myconfig)
                my_file.close()

    if myinteractive:
        # a break for when interactive bits are complete, before summary data
        print "==================================="

    #Print summary results
    for group in sorted(group_results.keys()):
        test_count = len(group_results[group])
        failures = group_failure_counts[group]
        total_failures = total_failures + failures
        if (failures > 0):
            print u'Test Group '+group+u' FAILED: '+ str((test_count-failures))+'/'+str(test_count) + u' Tests Passed!'
        else:
            print u'Test Group '+group+u' SUCCEEDED: '+ str((test_count-failures))+'/'+str(test_count) + u' Tests Passed!'

    return total_failures

def main(args):
    """
    Execute a test against the given base url.

    Keys allowed for args:
        url          - REQUIRED - Base URL
        test         - REQUIRED - Test file (yaml)
        print_bodies - OPTIONAL - print response body
        log          - OPTIONAL - set logging level {debug,info,warning,error,critical} (default=warning)
        interactive  - OPTIONAL - mode that prints info before and after test exectuion and pauses for user input for each test
    """

    if 'log' in args and args['log'] is not None:
        logging.basicConfig(level=LOGGING_LEVELS.get(args['log'].lower(), logging.NOTSET))

    test_structure = read_test_file(args['test'])
    tests = build_testsets(args['url'], test_structure)

    # Override configs from command line if config set
    for t in tests:
        if 'print_bodies' in args and args['print_bodies'] is not None:
            t.config.print_bodies = safe_to_bool(args['print_bodies'])

        if 'interactive' in args and args['interactive'] is not None:
            t.config.interactive = safe_to_bool(args['interactive'])

    # Execute all testsets
    failures = execute_testsets(tests)

    sys.exit(failures)

#Allow import into another module without executing the main method
if(__name__ == '__main__'):
    parser = argparse.ArgumentParser()
    parser.add_argument(u"url", help="Base URL to run tests against")
    parser.add_argument(u"test", help="Test file to use")
    parser.add_argument(u"--print-bodies", help="Print all response bodies", type=bool)
    parser.add_argument(u"--log", help="Logging level")
    parser.add_argument(u"--interactive", help="Interactive mode")
    args = vars(parser.parse_args())

    main(args)