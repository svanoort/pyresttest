import string
import os
import copy
import json
import StringIO
import pycurl
from contenthandling import ContentHandler
import validators
from parsing import *

"""
Pull out the Test objects and logic associated with them
This module implements the internal responsibilities of a test object:
- Test parameter/configuration storage
- Templating for tests
- Parsing of test configuration from results of YAML read
"""

DEFAULT_TIMEOUT = 10  # Seconds

#Map HTTP method names to curl methods
#Kind of obnoxious that it works this way...
HTTP_METHODS = {u'GET' : pycurl.HTTPGET,
    u'PUT' : pycurl.UPLOAD,
    u'POST' : pycurl.POST,
    u'DELETE'  : 'DELETE'}

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
    _url  = None
    expected_status = [200]  # expected HTTP status code or codes
    _body = None
    headers = dict() #HTTP Headers
    method = u'GET'
    group = u'Default'
    name = u'Unnamed'
    validators = None  # Validators for response body, IE regexes, etc
    stop_on_failure = False
    failures = None

    templates = None  # Dictionary of template to compiled template

    # Bind variables, generators, and contexts
    variable_binds = None
    generator_binds = None  # Dict of variable name and then generator name
    extract_binds = None  # Dict of variable name and extract function to run

    def ninja_copy(self):
        """ Optimization: limited copy of test object, for realize() methods
            This only copies fields changed vs. class, and keeps methods the same
        """
        output = Test()
        myvars = vars(self)
        output.__dict__ = myvars.copy()
        return output

    # Template handling logic
    def set_template(self, variable_name, template_string):
        """ Add a templating instance for variable given """
        if self.templates is None:
            self.templates = dict()
        self.templates[variable_name] = string.Template(template_string)

    def del_template(self, variable_name):
        """ Remove template instance, so we no longer use one for this test """
        if self.templates is not None and variable_name in self.templates:
            del self.templates[variable_name]

    def realize_template(self, variable_name, context):
        """ Realize a templated value, using variables from context
            Returns None if no template is set for that variable """
        val = None
        if context is None or self.templates is None or variable_name not in self.templates:
            return None
        return self.templates[variable_name].safe_substitute(context.get_values())

    # These are variables that can be templated
    def set_body(self, value):
        """ Set body, directly """
        self._body = value

    def get_body(self, context=None):
        """ Read body from file, applying template if pertinent """
        if self._body is None:
            return None
        elif isinstance(self._body, basestring):
            return self._body
        else:
            return self._body.get_content(context=context)

    body = property(get_body, set_body, None, 'Request body, if any (for POST/PUT methods)')

    NAME_URL = 'url'
    def set_url(self, value, isTemplate=False):
        """ Set URL, passing flag if using a template """
        if isTemplate:
            self.set_template(self.NAME_URL, value)
        else:
            self.del_template(self.NAME_URL)
        self._url = value

    def get_url(self, context=None):
        """ Get URL, applying template if pertinent """
        val = self.realize_template(self.NAME_URL, context)
        if val is None:
            val = self._url
        return val
    url = property(get_url, set_url, None, 'URL fragment for request')


    def update_context_before(self, context):
        """ Make pre-test context updates, by applying variable and generator updates """
        if self.variable_binds:
            context.bind_variables(self.variable_binds)
        if self.generator_binds:
            for key, value in self.generator_binds.items():
                context.bind_generator_next(key, value)

    def update_context_after(self, response_body, context):
        """ Run the extraction routines to update variables based on HTTP response body """
        if self.extract_binds:
            for key, value in self.extract_binds.items():
                result = value.extract(response_body, context=context)
                print 'Result: {0}'.format(result)
                context.bind_variable(key, result)


    def is_context_modifier(self):
        """ Returns true if context can be modified by this test
            (disallows caching of templated test bodies) """
        return self.variable_binds or self.generator_binds or self.extract_binds

    def is_dynamic(self):
        """ Returns true if this test does templating """
        if self.templates and self.templates.keys():
            return True
        elif isinstance(self._body, ContentHandler) and self._body.is_dynamic():
            return True
        return False

    def realize(self, context=None):
        """ Return a fully-templated test object, for configuring curl
            Warning: this is a SHALLOW copy, mutation of fields will cause problems!
            Can accept a None context """
        if not self.is_dynamic() or context is None:
            return self
        else:
            selfcopy = self.ninja_copy()
            selfcopy.templates = None
            if isinstance(self._body, ContentHandler):
                selfcopy._body = self._body.get_content(context)
            selfcopy._url = self.get_url(context=context)
            return selfcopy

    def realize_partial(self, context=None):
        """ Attempt to template out what is static if possible, and load files.
            Used for performance optimization, in cases where a test is re-run repeatedly
            WITH THE SAME Context.
        """

        if self.is_context_modifier():
            # Don't template what is changing
            return self
        elif self.is_dynamic():  # Dynamic but doesn't modify context, template everything
            return self.realize(context=context)

        # See if body can be replaced
        bod = self._body
        newbod = None
        if bod and isinstance(bod, ContentHandler) and bod.is_file and not bod.is_template_path:
            # File can be UN-lazy loaded
            newbod = bod.create_noread_version()

        output = self
        if newbod: # Read body
            output = copy.copy(self)
            output._body = newbod
        return output

    def __init__(self):
        self.headers = dict()
        self.expected_status = [200]
        self.templated = dict()

    def __str__(self):
        return json.dumps(self, default=safe_to_json)

    def configure_curl(self, timeout=DEFAULT_TIMEOUT, context=None, curl_handle=None):
        """ Create and mostly configure a curl object for test, reusing existing if possible """

        if curl_handle:
            curl = curl_handle
        else:
            curl = pycurl.Curl()

        # curl.setopt(pycurl.VERBOSE, 1)  # Debugging convenience
        curl.setopt(curl.URL, str(self.url))
        curl.setopt(curl.TIMEOUT, timeout)

        bod = self.body

        # Set read function for post/put bodies
        if self.method == u'POST' or self.method == u'PUT':
            curl.setopt(curl.READFUNCTION, StringIO.StringIO(bod).read)

        if self.method == u'POST':
            curl.setopt(HTTP_METHODS[u'POST'], 1)
            if bod is not None:
                curl.setopt(pycurl.POSTFIELDSIZE, len(bod))  # Required for some servers
        elif self.method == u'PUT':
            curl.setopt(HTTP_METHODS[u'PUT'], 1)
            if bod is not None:
                curl.setopt(pycurl.INFILESIZE, len(bod))  # Required for some servers
        elif self.method == u'DELETE':
            curl.setopt(curl.CUSTOMREQUEST,'DELETE')


        if self.headers: #Convert headers dictionary to list of header entries, tested and working
            headers = [str(headername)+':'+str(headervalue) for headername, headervalue in self.headers.items()]
        else:
            headers = list()
        headers.append("Expect:")  # Fix for expecting 100-continue from server, which not all servers will send!
        headers.append("Connection: close")
        curl.setopt(curl.HTTPHEADER, headers)
        return curl

    @classmethod
    def build_test(cls, base_url, node, input_test = None, test_path=None):
        """ Create or modify a test, input_test, using configuration in node, and base_url
        If no input_test is given, creates a new one

        Test_path gives path to test file, used for setting working directory in setting up input bodies

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
                temp = configvalue
                if isinstance(configvalue, dict):
                    # Template is used for URL
                    val = lowercase_keys(configvalue)[u'template']
                    assert isinstance(val,str) or isinstance(val,unicode) or isinstance(val,int)
                    url = base_url + unicode(val,'UTF-8').encode('ascii','ignore')
                    mytest.set_url(url, isTemplate=True)
                else:
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
            elif configelement == u'extract_binds':
                # Add a list of extractors, of format:
                # {variable_name: {extractor_type: extractor_config}, ... }
                binds = flatten_dictionaries(configvalue)
                if mytest.extract_binds is None:
                    mytest.extract_binds = dict()

                for variable_name, extractor in binds.items():
                    if not isinstance(extractor, dict) or len(extractor) == 0:
                        raise TypeError("Extractors must be defined as maps of extractorType:{configs} with 1 entry")
                    if len(extractor) > 1:
                        raise ValueError("Cannot define multiple extractors for given variable name")
                    extractor_type, extractor_config = extractor.items()[0]
                    extractor = validators.parse_extractor(extractor_type, extractor_config)
                    mytest.extract_binds[variable_name] = extractor

            elif configelement == u'validators':
                # Add a list of validators
                if not isinstance(configvalue, list):
                    raise Exception('Misconfigured validator section, must be a list of validators')
                if mytest.validators is None:
                    mytest.validators = list()

                # create validator and add to list of validators
                for var in configvalue:
                    if not isinstance(var, dict):
                        raise TypeError("Validators must be defined as validatorType:{configs} ")
                    for validator_type, validator_config in var.items():
                        validator = validators.parse_validator(validator_type, validator_config)
                        mytest.validators.append(validator)

            elif configelement == u'body': #Read request body, as a ContentHandler
                # Note: os.path.expandirs removed
                mytest.body = ContentHandler.parse_content(configvalue)
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
            elif configelement == 'variable_binds':
                mytest.variable_binds = flatten_dictionaries(configvalue)
            elif configelement == 'generator_binds':
                output = flatten_dictionaries(configvalue)
                output2 = dict()
                for key, value in output.items():
                    output2[str(key)] = str(value)
                mytest.generator_binds = output2
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