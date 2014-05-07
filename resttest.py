import argparse
import yaml
import pycurl
import json 
from voluptuous import Schema, Required, All, Length, Range, Optional, MultipleInvalid, Invalid
#TODO set up and maintain Unicode safety! YAML and strings are unicode, bytes are bytes (reponse and request bodies)

#Map HTTP method names to curl methods
#Kind of obnoxious that it works this way...
HTTP_METHODS = {u'GET' : pycurl.HTTPGET,
    u'PUT' : pycurl.UPLOAD,
    u'POST' : pycurl.POST,
    u'DELETE' : 'DELETE'}

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
    'request_size' : pycurl.REQUEST_SIZE,
    'speed_download' : pycurl.SPEED_DOWNLOAD,
    'speed_upload' : pycurl.SPEED_UPLOAD,
    
    #Connection counts
    'redirect_count' : pycurl.REDIRECT_COUNT,
    'num_connects' : pycurl.NUM_CONNECTS

    #TODO custom implementation for requests per second and server processing time, separate from previous 
}

#TODO Use function definitions and reduce() with lambdas (or closures for internal state) to do aggregates
AGGREGATES = {
    'mean_arithmetic':None, #AKA the average, good for many things
    'mean_harmonic':None, #Harmonic mean, better predicts average of rates: http://en.wikipedia.org/wiki/Harmonic_mean
    'median':None,
    'std_deviation':None,
    '90_percentile':None #90th percentile, below which 90% of functions fall
}

    
#Schema for file objects -- imports and request bodies
__file_schema__ = { 
       Required('file'):All(str,Length(min=1))
}    

class Test:
    """ Describes a REST test, which may include a benchmark component """
    url  = None
    expected_status = [200] #expected HTTP status code or codes
    body = None #Request body, if any (for POST/PUT methods)
    headers = dict() #HTTP Headers
    method = u"GET"
    group = u'Default'
    name = u'Unnamed'    
    validators = None #Validators for response body, IE regexes, etc
    benchmark = None #Benchmarking config for item
    #In this case, config would be used by all tests following config definition, and in the same scope as tests
    
    __schema__ = [ #Schema for complex test definitions
        {Required(u'url'):All(unicode, Length(min=1))},
        {Optional(u'expected_status'):[]},
        {Optional(u'group'):All(unicode)},
        {Optional(u'name'):All(unicode)},
        {Optional(u'method'):[u'GET',u'PUT',u'POST',u'DELETE']},
    ]



    def __str__(self):
        print json.dumps(self)

class TestConfig:
    """ Configuration for a test run """
    timeout = 30 #timeout of tests, in seconds
    print_bodies = False #Print response bodies in all cases
    retries = 0 #Retries on failures
    verbose = False
    test_parallel = False #Allow parallel execution of tests in a test set, for speed?

    __schema__ = [{

    }] #Allows extra unknown keys

    def __str__(self):
        print json.dumps(self)

class TestSet:
    """ Encapsulates a set of tests and test configuration for them """
    tests = list()
    config = TestConfig()

    __schema__ = Schema([ #Overall test set schema for object converted to this
        {Optional(u'url'):All(str, Length(min=1))},
        {Optional(u'config'):TestConfig.__schema__},
        {Optional(u'test'):Test.__schema__},
        {Optional(u'import'):__file_schema__}        
    ], 
    extra=True)

class BenchmarkResult:
    """ Stores results from a benchmark for reporting use """
    aggregates = dict() #Map aggregate name (key) to aggregate value (value)
    #TODO aggregates act as a reduce operation on a metric result, doing stream-wise processing
    results = list() #Benchmark output

class BenchmarkConfig:
    """ Holds configuration specific to benchmarking of method """
    warmup_runs = 100 #Times call is executed to warm up
    benchmark_runs = 1000 #Times call is executed to generate benchmark results
    metrics = set() #Metrics to gather, TODO define these
    aggregates = set() #Aggregate options to report, TODO define these
    store_full = False #Store full statistics, not just aggregates
    #TODO output of full response set to CSV / JSON

    def __str__(self):
        print json.dumps(self)

class TestResponse:
    """ Encapsulates everything about a test response """   
    test = None #Test run
    response_code = None
    body = bytearray() #Response body, if tracked -- TODO use chunk or byte-array storage
    passed = False
    response_headers = bytearray()
    statistics = None #Used for benchmark stats on the method

    def __str__(self):
        print json.dumps(self)

    def body_callback(self, buf):
        """ Write response body by pyCurl callback """
        self.body.extend(buf)

    def unicode_body(self):
        return unicode(body,'UTF-8')        

    def header_callback(self,buf):
        """ Write headers by pyCurl callback """
        self.response_headers.extend(buf) #Optional TODO use chunk or byte-array storage    

def read_test_file(path):
    """ Read test file at 'path' in YAML """
    #TODO Add validation via voluptuous
    #TODO Handle multiple test sets in a given doc
    teststruct = yaml.safe_load(read_file(path))
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
    #returns a testconfig and collection of tests
    for node in test_structure: #Iterate through lists of test and configuration elements
        if isinstance(node,dict):
            node = lowercase_keys(node)
            for key in node:                
                if key == u'import':
                    importfile = node[key] #import another file
                    print u'Importing additional testset: '+importfile
                if key == u'url': #Simple test, just a GET to a URL
                    mytest = Test()
                    mytest.url = base_url + node[key]
                    tests_out.append(mytest)                                        
                if key == u'test': #Complex test with additional parameters
                    child = node[key]
                    mytest = make_test(base_url, child)                    
                    tests_out.append(mytest)                    
                if key == u'config' or key == u'configuration':
                    test_config = make_configuration(node[key])
                    print 'Configuration: ' + json.dumps(node[key])
    testset = TestSet()
    testset.tests = tests_out
    testset.config = test_config
    return [testset]

def validate_testset(testset):
    """ Validate a testset data structure, return boolean if it's valid, else print errors  """

    return TestSet.__schema__(testset) #Schema is stored in the class itself 


def make_configuration(node):
    """ Convert input object to configuration information """
    test_config = TestConfig()        

    node = lowercase_keys(flatten_dictionaries(node)) #Make it usable    

    for key, value in node.items():
        if key == u'timeout':
            test_config.timeout = int(value)
        elif key == u'print_bodies':
            test_config.print_bodies = bool(value)
        elif key == u'retries':
            test_config.retries = int(value)
        elif key == u'verbose':
            test_config.verbose = bool(value)

    return test_config

def flatten_dictionaries(input):
    """ Flatten a list of dictionaries into a single dictionary, to allow flexible YAML use
      Dictionary comprehensions can do this, but would like to allow for pre-Python 2.7 use 
      If input isn't a list, just return it.... """
    output = dict()
    if isinstance(input,list):
        for map in input:
            if not isinstance(map,dict):
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

def make_test(base_url, node):
    """ Create a test using explicitly specified elements from the test input structure 
     to make life *extra* fun, we need to handle list <-- > dict transformations. 

     This is to say: list(dict(),dict()) or dict(key,value) -->  dict() for some elements 

     Accepted structure must be a single dictionary of key-value pairs for test configuration """
    mytest = Test()
    node = lowercase_keys(flatten_dictionaries(node)) #Clean up for easy parsing
    
    #Copy/convert input elements into appropriate form for a test object
    for configelement, configvalue in node.items(): 
        #Configure test using configuration elements            
        if configelement == u'url':
            mytest.url = base_url + str(configvalue)
        elif configelement == u'method': #Http method, converted to uppercase string
            mytest.method = str(configvalue).upper()                 
        elif configelement == u'group': #Test group
            mytest.group = str(configvalue)
        elif configelement == u'name': #Test name
            mytest.name = str(configvalue)
        elif configelement == u'validators':
            raise NotImplementedError() #TODO implement validators by regex, or file/schema match
        elif configelement == u'benchmark':
            raise NotImplementedError() #TODO implement benchmarking routines
        
        elif configelement == u'body': #Read request body, either as inline input or from file            
            if isinstance(configvalue, dict) and u'file' in lowercase_keys(body):
                mytest.body = read_file(body[u'file']) #TODO change me to pass in a file handle, rather than reading all bodies into RAM
            elif isinstance(configvalue, str):
                mytest.body = configvalue
            else:
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



def run_test(mytest, test_config = TestConfig()):
    """ Run actual test, return results """
    if not isinstance(mytest, Test):
        raise Exception('Need to input a Test type object')
    if not isinstance(test_config, TestConfig):
        raise Exception('Need to input a TestConfig type object for the testconfig')
    
    curl = pycurl.Curl()
    curl.setopt(curl.URL,mytest.url)
    curl.setopt(curl.TIMEOUT,test_config.timeout)

    #if mytest.body:
    #TODO use file objects for CURLOPT_READDATA http://pycurl.sourceforge.net/doc/files.html
    #OR if not file, use CURLOPT_READFUNCTION


    #TODO Handle get/put/post/delete method settings
    #Needs to set curl.POSTFIELDS option to do a POST
    if mytest.method == u'POST':
        pass
    elif mytest.method == u'PUT':
        pass
    elif mytest.method == u'DELETE':
        curl.setopt(curl.CUSTOMREQUEST,'DELETE')
    
    if mytest.headers: #Convert headers dictionary to list of header entries, tested and working
        headers = list()
        for headername, headervalue in mytest.headers.items():
            headers.append(str(headername) + ': ' +str(headervalue))
        curl.setopt(curl.HTTPHEADER, headers) #Need to read from headers

    result = TestResponse()
    curl.setopt(pycurl.WRITEFUNCTION, result.body_callback)
    curl.setopt(pycurl.HEADERFUNCTION,result.header_callback) #Gets headers
    
    try:
        curl.perform() #Run the actual call
    except Exception as e: 
        print e  #TODO figure out how to handle failures where no output is generated IE connection refused
        
    result.test = mytest
    response_code = curl.getinfo(pycurl.RESPONSE_CODE)
    result.response_code = response_code
    result.passed = response_code in mytest.expected_status 

    print str(test_config.print_bodies) + ',' + str(not result.passed) + ' , ' + str(test_config.print_bodies or not result.passed)
    
    #Print response body if override is set to print all *OR* if test failed (to capture maybe a stack trace)
    if test_config.print_bodies or not result.passed:
        #TODO figure out why this prints for ALL methods if any of them fail!!!
        print result.body

    curl.close()

    result.body = None #Remove the body, we do NOT need to waste the memory anymore
    return result

def benchmark(curl, benchmark_config):
    """ Perform a benchmark, (re)using a given, configured CURL call to do so """
    curl.setopt(pycurl.WRITEFUNCTION, lambda x: None) #Do not store actual response body at all. 
    warmup_runs = benchmark_config.warmup_runs
    benchmark_runs = benchmark_config.benchmark_runs
    message = ''  #Message is name of benchmark... print it?

    # Source: http://pycurl.sourceforge.net/doc/curlobject.html
    # http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html -- this is the info parameters, used for timing, etc
    info_fetch = {'response_code':pycurl.RESPONSE_CODE,
        'pretransfer_time':pycurl.PRETRANSFER_TIME,
        'starttransfer_time':pycurl.STARTTRANSFER_TIME,
        'size_download':pycurl.SIZE_DOWNLOAD,
        'total_time':pycurl.TOTAL_TIME
    }

    #Benchmark warm-up to allow for caching, JIT compiling, etc
    print 'Warmup: ' + message + ' started'
    for x in xrange(0, warmup_runs):
        curl.perform()
    print 'Warmup: ' + message + ' finished'

    bytes = dict()
    speed = dict()
    time_pre = dict()
    time_server = dict()
    time_xfer = dict()

    print 'Benchmark: ' + message + ' starting'
    for x in xrange(0, benchmark_runs):
        curl.perform()
        if curl.getinfo(pycurl.RESPONSE_CODE) != 200:
            raise Exception('Error: failed call to service!')

        time_pretransfer = curl.getinfo(pycurl.PRETRANSFER_TIME) #Time to negotiate connection, before server starts response negotiation
        time_starttransfer = curl.getinfo(pycurl.STARTTRANSFER_TIME) #Pre-transfer time until server has generated response, just before first byte sent
        time_total = curl.getinfo(pycurl.TOTAL_TIME) #Download included

        time_xfer[x] = time_total - time_starttransfer
        time_server[x] = time_starttransfer - time_pretransfer
        time_pre[x] = time_pretransfer

        bytes[x] = curl.getinfo(pycurl.SIZE_DOWNLOAD) #bytes
        speed[x] = curl.getinfo(pycurl.SPEED_DOWNLOAD) #bytes/sec

        if print_intermediate:
            print 'Bytes: {size}, speed (MB/s) {speed}'.format(size=bytes[x],speed=speed[x]/(1024*1024))
            print 'Pre-transfer, server processing, and transfer times: {pre}/{server}/{transfer}'.format(pre=time_pretransfer,server=time_server[x],transfer=time_xfer[x])

    #print info
    print 'Benchmark: ' + message + ' ending'

    print 'Benchmark results for ' + message + ' Average bytes {bytes}, average transfer speed (MB/s): {speed}'.format(
        bytes=sum(bytes.values())/benchmark_runs,
        speed=sum(speed.values())/(benchmark_runs*1024*1024)
    )

    print 'Benchmark results for ' + message + ' Avg pre/server/xfer time (s) {pre}/{server}/{transfer}'.format(
        pre=sum(time_pre.values())/benchmark_runs,
        server=sum(time_server.values())/benchmark_runs,
        transfer=sum(time_xfer.values())/benchmark_runs
    )

    pass


def execute_tests(testset):
    """ Execute a set of tests, using given TestSet input """
    mytests = testset.tests
    myconfig = testset.config
    group_results = dict() #results, by group 
    group_failure_counts = dict()   

    #Initialize the dictionaries to store test fail counts and results
    for test in mytests:
        group_results[test.group] = list()
        group_failure_counts[test.group] = 0


    #Make sure we actually have tests to execute
    if not mytests:
        return None

    #Run tests, collecting statistics as needed
    for test in mytests: 
        result = run_test(test, test_config = myconfig)        
        
        if not result.passed: #Print failure, increase failure counts for that test group
            print 'Test Failed: '+test.name+" URL="+test.url+" Group="+test.group+" HTTP Status Code: "+str(result.response_code)
            
            #Increment test failure counts for that group (adding an entry if not present)
            failures = group_failure_counts[test.group]
            failures = failures + 1
            group_failure_counts[test.group] = failures

        else: #Test passed, print results if verbose mode is on
            if myconfig.verbose:
                print 'Test Succeeded: '+test.name+" URL="+test.url+" Group="+test.group

        #Add to results for this test group to the resultset
        group_results[test.group].append(result)        

    #Print summary results
    for group in sorted(group_results.keys()):
        test_count = len(group_results[group])
        failures = group_failure_counts[group]
        if (failures > 0):
            print u'Test Group '+group+u' FAILED: '+ str((test_count-failures))+'/'+str(test_count) + u' Tests Passed!'            
        else:
            print u'Test Group '+group+u' SUCCEEDED: '+ str((test_count-failures))+'/'+str(test_count) + u' Tests Passed!'



#Allow import into another module without executing the main method
if(__name__ == '__main__'):
    parser = argparse.ArgumentParser()
    parser.add_argument(u"url", help="Base URL to run tests against")
    parser.add_argument(u"test", help="Test file to use")
    parser.add_argument(u"--verbose", help="Verbose output")
    parser.add_argument(u"--print-bodies", help="Print all response bodies", type=bool)
    args = parser.parse_args()
    test_structure = read_test_file(args.test)
    tests = build_testsets(args.url, test_structure)
    
    #Override testset verbosity if given as command-line argument
    if args.verbose: 
        tests.config.verbose = True

    #Execute batches of testsets
    for testset in tests:
        execute_tests(testset)    