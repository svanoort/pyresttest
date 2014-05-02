import argparse
import yaml
import pycurl


HTTP_METHODS = ['GET','PUT','POST','DELETE']

class Test:
    """ Describes a REST test """
    url  = None
    expected_status = [200,204] #expected HTTP status code or codes
    body = None #Request body, if any (for POST/PUT methods)
    headers = dict() #HTTP Headers
    method = "GET"
    group = 'Default'
    name = 'Unnamed'
    

class TestConfig:
    """ Configuration for a test run """
    timeout = 30 #timeout of tests, in seconds
    print_bodies = False
    repeats = 0 
    verbose = False

class TestResponse: 
    """ Encapsulates everything about a test response """   
    test = None #Test run
    response_code = None
    body = "" #Response body, if tracked
    passed = False
    response_headers = ""
    benchmark = False    
    statistics = None #Used for benchmark stats on the method

    def body_callback(self, buf): #Callback for when we actually want the method body back
        self.body = self.body + buf

    def header_callback(self,buf):
        self.response_headers = self.response_headers + buf

def read_test_file(path):
    """ Read test file at 'path' in YAML and convert to a test structure
    existing_files is used when importing tests into other tests to prevent loops """

    f = open(path, "r")
    string = f.read()
    f.close()
    teststruct = yaml.load(string)
    return teststruct

def build_tests(tests, test_files = set() ):
    """ Convert a YAML structure to a set of structured tests
    test_files is used for tests that import to avoid recursive loops """
    return None


def test(mytest, test_config = TestConfig()):
    """ Run actual test, return results """
    if not isinstance(mytest, Test):
        raise Exception('Need to input a Test type object')
    if not isinstance(mytest, TestConfig):
        raise Exception('Need to input a TestConfig type object for the testconfig')
    
    curl = pycurl.Curl()

    curl.setopt(curl.URL,mytest.url)
    curl.setopt(curl.TIMEOUT,test_config.timeout)
    #TODO Handle get/put/post/delete method settings
    #Needs to set curl.POSTFIELDS option to do a POST
    if mytest.headers:
        for header in mytest.headers:
            #curl.setopt(curl.HTTPHEADER, '[Accept: application/json]') #Need to read from headers
            pass #TODO handle setting headers on requests

    result = TestResponse()
    if not test_config.print_bodies: #Silence handling of response bodies
        curl.setopt(pycurl.WRITEFUNCTION, lambda x: None)
    else:
        curl.setopt(pycurl.WRITEFUNCTION, result.body_callback)
    curl.setopt(pycurl.HEADERFUNCTION,result.header_callback) #Gets headers
    curl.perform() #Run the actual call
    
    
    result.test = mytest
    response_code = curl.getinfo(pycurl.RESPONSE_CODE)
    result.response_code = response_code
    result.passed = response_code in mytest.expected_status 

    if not test_config.print_bodies:
        print result.body

    curl.close()
    return result


def execute_tests(mytests, test_config = TestConfig() ):
    """ Execute a set of tests """
    group_results = dict() #results, by group 
    group_failure_counts = dict()   

    #Make sure we actually have tests to execute
    if not mytests:
        return None

    #Run tests, collecting statistics as needed
    for test in mytests: 
        result = test(test, test_config = test_config)

        failures = group_failure_counts[test.group]
        if not result.passed:
            print 'Test Failed: '+test.name+" URL="+test.url+" Group="+test.group            
            
            #Increment test failure counts for that group (adding an entry if not present)
            if not failures:
                failures = 0
            failures = failures + 1
            group_failure_counts[test.group] = failures

        else:
            if test_config.verbose:
                print 'Test Succeeded: '+test.name+" URL="+test.url+" Group="+test.group

        #Add to results for this test group
        grouping = group_results[test.group]
        if (grouping): #Have tests for this test group
            grouping.append(result)
        else:
            grouping = [result]

    #Print summary results
    for group in sorted(group_results.keys()):
        test_count = len(group_results[group])
        failures = group_failure_counts[group]
        if (failures > 0):
            print 'Test Group '+group+' FAILED: '+ (test_count-failures)/test_count + 'Tests Passed!'
        else:
            print 'Test Group '+group+' SUCCEEDED: '+ (test_count-failures)/test_count + 'Tests Passed!'



#Allow import into another module without executing the main method
if(__name__ == '__main__'):
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Base URL to run tests against")
    parser.add_argument("test", help="Test file to use")
    parser.add_argument("--verbose", help="Verbose output")
    args = parser.parse_args()
    print args.url
    print args.test
    testset = read_test_file(args.test)
    print testset