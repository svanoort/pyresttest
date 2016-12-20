import string
import os
import copy
import json
import traceback
import pycurl
import sys

from .binding import Context
from . import contenthandling
from .contenthandling import ContentHandler
from . import validators
from .validators import Failure
from . import parsing
from .parsing import *
from .macros import *

# Find the best implementation available on this platform
try:
    from cStringIO import StringIO as MyIO
except:
    try:
        from StringIO import StringIO as MyIO
    except ImportError:
        from io import BytesIO as MyIO

# Python 2/3 switches
PYTHON_MAJOR_VERSION = sys.version_info[0]
if PYTHON_MAJOR_VERSION > 2:
    import urllib.parse as urlparse
    from past.builtins import basestring
else:
    import urlparse

# Python 3 compatibility shims
from . import six
from .six import binary_type
from .six import text_type
from .six import iteritems
from .six.moves import filter as ifilter

"""
Pull out the Test objects and logic associated with them
This module implements the internal responsibilities of a test object:
- Test parameter/configuration storage
- Templating for tests
- Parsing of test configuration from results of YAML read
"""

BASECURL = pycurl.Curl()  # Used for some validation/parsing

DEFAULT_TIMEOUT = 10  # Seconds

# Map HTTP method names to curl methods
# Kind of obnoxious that it works this way...
HTTP_METHODS = {u'GET': pycurl.HTTPGET,
                u'PUT': pycurl.UPLOAD,
                u'PATCH': pycurl.POSTFIELDS,
                u'POST': pycurl.POST,
                u'DELETE': 'DELETE'}

# Parsing helper functions
def coerce_to_string(val):
    if isinstance(val, text_type):
        return val
    elif isinstance(val, int):
        return text_type(val)
    elif isinstance(val, binary_type):
        return val.decode('utf-8')
    else:
        raise TypeError("Input {0} is not a string or integer, and it needs to be!".format(val))

def coerce_string_to_ascii(val):
    if isinstance(val, text_type):
        return val.encode('ascii')
    elif isinstance(val, binary_type):
        return val
    else:
        raise TypeError("Input {0} is not a string, string expected".format(val))

def coerce_http_method(val):
    myval = val
    if not isinstance(myval, basestring) or len(val) == 0:
        raise TypeError("Invalid HTTP method name: input {0} is not a string or has 0 length".format(val))
    if isinstance(myval, binary_type):
        myval = myval.decode('utf-8')
    return myval.upper()

def coerce_list_of_ints(val):
    """ If single value, try to parse as integer, else try to parse as list of integer """
    if isinstance(val, list):
        return [int(x) for x in val]
    else:
        return [int(val)]

class Test(Macro):
    """ Describes a REST test """
    _url = None
    expected_status = [200]  # expected HTTP status code or codes
    _body = None
    _headers = dict()  # HTTP Headers
    method = u'GET'
    group = u'Default'
    name = u'Unnamed'
    validators = None  # Validators for response body, IE regexes, etc
    stop_on_failure = False
    failures = None
    auth_username = None
    auth_password = None
    auth_type = pycurl.HTTPAUTH_BASIC
    delay = 0
    curl_options = None

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

    body = property(get_body, set_body, None,
                    'Request body, if any (for POST/PUT methods)')

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

    NAME_HEADERS = 'headers'
    # Totally different from others

    def set_headers(self, value, isTemplate=False):
        """ Set headers, passing flag if using a template """
        if isTemplate:
            self.set_template(self.NAME_HEADERS, 'Dict_Templated')
        else:
            self.del_template(self.NAME_HEADERS)
        self._headers = value

    def get_headers(self, context=None):
        """ Get headers, applying template if pertinent """
        if not context or not self.templates or self.NAME_HEADERS not in self.templates:
            return self._headers

        # We need to apply templating to both keys and values
        vals = context.get_values()

        def template_tuple(tuple_input):
            return (string.Template(str(tuple_item)).safe_substitute(vals) for tuple_item in tuple_input)
        return dict(map(template_tuple, self._headers.items()))

    headers = property(get_headers, set_headers, None,
                       'Headers dictionary for request')

    def update_context_before(self, context):
        """ Make pre-test context updates, by applying variable and generator updates """
        if self.variable_binds:
            context.bind_variables(self.variable_binds)
        if self.generator_binds:
            for key, value in self.generator_binds.items():
                context.bind_generator_next(key, value)

    def update_context_after(self, response_body, headers, context):
        """ Run the extraction routines to update variables based on HTTP response body """
        if self.extract_binds:
            for key, value in self.extract_binds.items():
                result = value.extract(
                    body=response_body, headers=headers, context=context)
                context.bind_variable(key, result)

    def is_context_modifier(self):
        """ Returns true if context can be modified by this test
            (disallows caching of templated test bodies) """
        return self.variable_binds or self.generator_binds or self.extract_binds

    def is_dynamic(self):
        """ Returns true if this test does templating """
        if self.templates:
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
            selfcopy._headers = self.get_headers(context=context)
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
        if newbod:  # Read body
            output = copy.copy(self)
            output._body = newbod
        return output

    def __init__(self):
        self.headers = dict()
        self.expected_status = [200]
        self.templated = dict()

    def __str__(self):
        return json.dumps(self, default=safe_to_json)

    def execute_macro(self, testset_config=TestSetConfig(), context=None, cmdline_args=None, callbacks=MacroCallbacks(), curl_handle=None, *args, **kwargs):
        """ Put together test pieces: configure & run actual test, return results """

        mytest=self

        # Initialize a context if not supplied, and do context updates
        my_context = context
        if my_context is None:
            my_context = Context()
        mytest.update_context_before(my_context)
        

        # Pre-run initialization of object, generate executable test objects
        templated_test = mytest.realize(my_context)
        result = TestResponse()
        result.test = templated_test
        result.passed = None

        # Request setup
        curl = templated_test.configure_curl(
            timeout=testset_config.timeout, context=my_context, curl_handle=curl_handle)
        headers = MyIO()
        body = MyIO()
        curl.setopt(pycurl.WRITEFUNCTION, body.write)
        curl.setopt(pycurl.HEADERFUNCTION, headers.write)
        if testset_config.verbose:
            curl.setopt(pycurl.VERBOSE, True)
        if testset_config.ssl_insecure:
            curl.setopt(pycurl.SSL_VERIFYPEER, 0)
            curl.setopt(pycurl.SSL_VERIFYHOST, 0)        

        # Pre-request work, wait for input or add a delay before the request runs
        if testset_config.interactive:
            callbacks.log_status("===================================")
            callbacks.log_status("%s" % mytest.name)
            callbacks.log_status("-----------------------------------")
            callbacks.log_status("REQUEST:")
            callbacks.log_status("%s %s" % (templated_test.method, templated_test.url))
            callbacks.log_status("HEADERS:")
            callbacks.log_status("%s" % (templated_test.headers))
            if mytest.body is not None:
                callbacks.log_status("\n%s" % templated_test.body)
            raw_input("Press ENTER when ready (%d): " % (mytest.delay))

        if mytest.delay > 0:
            callbacks.log_status("Delaying for %ds" % mytest.delay)
            time.sleep(mytest.delay)

        # Execute the test, and handle errors
        try:
            curl.perform()  # Run the actual call
        except Exception as e:
            # Curl exception occurred (network error), do not pass go, do not
            # collect $200
            trace = traceback.format_exc()
            result.failures.append(Failure(message="Curl Exception: {0}".format(
                e), details=trace, failure_type=validators.FAILURE_CURL_EXCEPTION))
            result.passed = False
            curl.close()
            return result

        # Post-request work: perform cleanup and gather info from the request as needed
        response_code = curl.getinfo(pycurl.RESPONSE_CODE)
        result.response_code = response_code
        result.body = body.getvalue()
        body.close()
        result.response_headers = text_type(headers.getvalue(), HEADER_ENCODING)  # Per RFC 2616
        headers.close()
        
        # We are now done with the request, now we can do all the analysis and reporting
        # This uses the result object and result bodies + test config

        callbacks.log_intermediate("Initial Test Result, based on expected response code: " +
                     str(response_code in mytest.expected_status))

        if response_code in mytest.expected_status:
            result.passed = True
        else:
            # Invalid response code
            result.passed = False
            failure_message = "Invalid HTTP response code: response code {0} not in expected codes [{1}]".format(
                response_code, mytest.expected_status)
            result.failures.append(Failure(
                message=failure_message, details=None, failure_type=validators.FAILURE_INVALID_RESPONSE))

        # Parse HTTP headers
        try:
            result.response_headers = parse_headers(result.response_headers)
        except Exception as e:
            trace = traceback.format_exc()
            result.failures.append(Failure(message="Header parsing exception: {0}".format(
                e), details=trace, failure_type=validators.FAILURE_TEST_EXCEPTION))
            result.passed = False
            curl.close()
            return result

        # print str(testset_config.print_bodies) + ',' + str(not result.passed) + ' ,
        # ' + str(testset_config.print_bodies or not result.passed)

        head = result.response_headers

        # execute validator on body
        if result.passed is True:
            body = result.body
            if mytest.validators is not None and isinstance(mytest.validators, list):
                callbacks.log_intermediate("executing this many validators: " +
                             str(len(mytest.validators)))
                failures = result.failures
                for validator in mytest.validators:
                    validate_result = validator.validate(
                        body=body, headers=head, context=my_context)
                    if not validate_result:
                        result.passed = False
                    # Proxy for checking if it is a Failure object, because of
                    # import issues with isinstance there
                    if hasattr(validate_result, 'details'):
                        failures.append(validate_result)
                    # TODO add printing of validation for interactive mode
            else:
                callbacks.log_intermediate("no validators found")

            # Only do context updates if test was successful
            mytest.update_context_after(result.body, head, my_context)

        # Print response body if override is set to print all *OR* if test failed
        # (to capture maybe a stack trace)
        if testset_config.print_bodies or not result.passed:
            if testset_config.interactive:
                callbacks.log_status("RESPONSE:")
            callbacks.log_status(result.body.decode(ESCAPE_DECODING))

        if testset_config.print_headers or not result.passed:
            if testset_config.interactive:
                callbacks.log_status("RESPONSE HEADERS:")
            callbacks.log_status(result.response_headers)

        # TODO add string escape on body output
        callbacks.log_intermediate(result)

        return result

    def configure_curl(self, timeout=DEFAULT_TIMEOUT, context=None, curl_handle=None):
        """ Create and mostly configure a curl object for test, reusing existing if possible """

        if curl_handle:
            curl = curl_handle

            try:  # Check the curl handle isn't closed, and reuse it if possible
                curl.getinfo(curl.HTTP_CODE)                
                # Below clears the cookies & curl options for clean run
                # But retains the DNS cache and connection pool
                curl.reset()
                curl.setopt(curl.COOKIELIST, "ALL")
            except pycurl.error:
                curl = pycurl.Curl()
            
        else:
            curl = pycurl.Curl()

        # curl.setopt(pycurl.VERBOSE, 1)  # Debugging convenience
        curl.setopt(curl.URL, str(self.url))
        curl.setopt(curl.TIMEOUT, timeout)

        is_unicoded = False
        bod = self.body
        if isinstance(bod, text_type):  # Encode unicode
            bod = bod.encode('UTF-8')
            is_unicoded = True

        # Set read function for post/put bodies
        if bod and len(bod) > 0:
            curl.setopt(curl.READFUNCTION, MyIO(bod).read)

        if self.auth_username and self.auth_password:
            curl.setopt(pycurl.USERPWD, 
                parsing.encode_unicode_bytes(self.auth_username) + b':' + 
                parsing.encode_unicode_bytes(self.auth_password))
            if self.auth_type:
                curl.setopt(pycurl.HTTPAUTH, self.auth_type)

        if self.method == u'POST':
            curl.setopt(HTTP_METHODS[u'POST'], 1)
            # Required for some servers
            if bod is not None:
                curl.setopt(pycurl.POSTFIELDSIZE, len(bod))
            else:
                curl.setopt(pycurl.POSTFIELDSIZE, 0)
        elif self.method == u'PUT':
            curl.setopt(HTTP_METHODS[u'PUT'], 1)
            # Required for some servers
            if bod is not None:
                curl.setopt(pycurl.INFILESIZE, len(bod))
            else:
                curl.setopt(pycurl.INFILESIZE, 0)
        elif self.method == u'PATCH':
            curl.setopt(curl.POSTFIELDS, bod)
            curl.setopt(curl.CUSTOMREQUEST, 'PATCH')
            # Required for some servers
            # I wonder: how compatible will this be?  It worked with Django but feels iffy.
            if bod is not None:
                curl.setopt(pycurl.INFILESIZE, len(bod))
            else:
                curl.setopt(pycurl.INFILESIZE, 0)
        elif self.method == u'DELETE':
            curl.setopt(curl.CUSTOMREQUEST, 'DELETE')
            if bod is not None:
                curl.setopt(pycurl.POSTFIELDS, bod)
                curl.setopt(pycurl.POSTFIELDSIZE, len(bod))
        elif self.method == u'HEAD':
            curl.setopt(curl.NOBODY, 1)
            curl.setopt(curl.CUSTOMREQUEST, 'HEAD')
        elif self.method and self.method.upper() != 'GET':  # Alternate HTTP methods
            curl.setopt(curl.CUSTOMREQUEST, self.method.upper())
            if bod is not None:
                curl.setopt(pycurl.POSTFIELDS, bod)
                curl.setopt(pycurl.POSTFIELDSIZE, len(bod))

        # Template headers as needed and convert headers dictionary to list of header entries
        
        head = self.get_headers(context=context)
        head = copy.copy(head)  # We're going to mutate it, need to copy

        # Set charset if doing unicode conversion and not set explicitly
        # TESTME
        if is_unicoded and u'content-type' in head.keys():
            content = head[u'content-type']
            if u'charset' not in content:
                head[u'content-type'] = content + u' ; charset=UTF-8'

        if head:
            headers = [str(headername) + ':' + str(headervalue)
                       for headername, headervalue in head.items()]
        else:
            headers = list()
        # Fix for expecting 100-continue from server, which not all servers
        # will send!
        headers.append("Expect:")
        headers.append("Connection: close")
        curl.setopt(curl.HTTPHEADER, headers)

        # Set custom curl options, which are KEY:VALUE pairs matching the pycurl option names
        # And the key/value pairs are set
        if self.curl_options:
            filterfunc = lambda x: x[0] is not None and x[1] is not None  # Must have key and value
            for (key, value) in ifilter(filterfunc, self.curl_options.items()):
                # getattr to look up constant for variable name
                curl.setopt(getattr(curl, key), value)
        return curl

    @classmethod
    def parse_test(cls, base_url, node, input_test=None, test_path=None):
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

        # Clean up for easy parsing
        node = lowercase_keys(flatten_dictionaries(node))

        # Simple table of variable name, coerce function, and optionally special store function
        CONFIG_ELEMENTS = {
            # Simple variables
            u'auth_username': [coerce_string_to_ascii],
            u'auth_password': [coerce_string_to_ascii],
            u'method': [coerce_http_method], # HTTP METHOD
            u'delay': [lambda x: int(x)], # Delay before running
            u'group': [coerce_to_string], # Test group name
            u'name': [coerce_to_string],  # Test name
            u'expected_status': [coerce_list_of_ints],
            u'delay': [lambda x: int(x)],
            u'stop_on_failure': [safe_to_bool],

            # Templated / special handling
            #u'url': [coerce_templatable, set_templated),  # TODO: special handling for templated content, sigh
            u'body': [ContentHandler.parse_content]
            #u'headers': [],

            # COMPLEX PARSE OPTIONS
            #u'extract_binds':[],  # Context variable-to-extractor output binding
            #u'variable_binds': [],  # Context variable to value binding
            #u'generator_binds': [],  # Context variable to generator output binding
            #u'validators': [],  # Validation functions to run
        }

        def use_config_parser(configobject, configelement, configvalue):
            """ Try to use parser bindings to find an option for parsing and storing config element
                :configobject: Object to store configuration
                :configelement: Configuratione element name
                :configvalue: Value to use to set configuration
                :returns: True if found match for config element, False if didn't
            """

            myparsing = CONFIG_ELEMENTS.get(configelement)
            if myparsing:
                converted = myparsing[0](configvalue)
                setattr(configobject, configelement, converted)
                return True
            return False

        # Copy/convert input elements into appropriate form for a test object
        for configelement, configvalue in node.items():
            if use_config_parser(mytest, configelement, configvalue):
                continue

            # Configure test using configuration elements
            if configelement == u'url':
                temp = configvalue
                if isinstance(configvalue, dict):
                    # Template is used for URL
                    val = lowercase_keys(configvalue)[u'template']
                    assert isinstance(val, basestring) or isinstance(val, int)
                    url = urlparse.urljoin(base_url, coerce_to_string(val))
                    mytest.set_url(url, isTemplate=True)
                else:
                    assert isinstance(configvalue, basestring) or isinstance(
                        configvalue, int)
                    mytest.url = urlparse.urljoin(base_url, coerce_to_string(configvalue))
            elif configelement == u'extract_binds':
                # Add a list of extractors, of format:
                # {variable_name: {extractor_type: extractor_config}, ... }
                binds = flatten_dictionaries(configvalue)
                if mytest.extract_binds is None:
                    mytest.extract_binds = dict()

                for variable_name, extractor in binds.items():
                    if not isinstance(extractor, dict) or len(extractor) == 0:
                        raise TypeError(
                            "Extractors must be defined as maps of extractorType:{configs} with 1 entry")
                    if len(extractor) > 1:
                        raise ValueError(
                            "Cannot define multiple extractors for given variable name")

                    # Safe because length can only be 1
                    for extractor_type, extractor_config in extractor.items():
                        mytest.extract_binds[variable_name] = validators.parse_extractor(extractor_type, extractor_config)


            elif configelement == u'validators':
                # Add a list of validators
                if not isinstance(configvalue, list):
                    raise Exception(
                        'Misconfigured validator section, must be a list of validators')
                if mytest.validators is None:
                    mytest.validators = list()

                # create validator and add to list of validators
                for var in configvalue:
                    if not isinstance(var, dict):
                        raise TypeError(
                            "Validators must be defined as validatorType:{configs} ")
                    for validator_type, validator_config in var.items():
                        validator = validators.parse_validator(
                            validator_type, validator_config)
                        mytest.validators.append(validator)

            elif configelement == 'headers':  # HTTP headers to use, flattened to a single string-string dictionary
                mytest.headers
                configvalue = flatten_dictionaries(configvalue)

                if isinstance(configvalue, dict):
                    filterfunc  = lambda x: str(x[0]).lower() == 'template'  # Templated items
                    templates = [x for x in ifilter(filterfunc, configvalue.items())]
                else:
                    templates = None

                if templates:
                    # Should have single entry in dictionary keys
                    mytest.set_headers(templates[0][1], isTemplate=True)
                elif isinstance(configvalue, dict):
                    mytest.headers = configvalue
                else:
                    raise TypeError(
                        "Illegal header type: headers must be a dictionary or list of dictionary keys")
            elif configelement == 'variable_binds':
                mytest.variable_binds = flatten_dictionaries(configvalue)
            elif configelement == 'generator_binds':
                output = flatten_dictionaries(configvalue)
                output2 = dict()
                for key, value in output.items():
                    output2[str(key)] = str(value)
                mytest.generator_binds = output2
            elif configelement.startswith('curl_option_'):
                curlopt = configelement[12:].upper()
                if hasattr(BASECURL, curlopt):
                    if not mytest.curl_options:
                        mytest.curl_options = dict()
                    mytest.curl_options[curlopt] = configvalue
                else:
                    raise ValueError(
                        "Illegal curl option: {0}".format(curlopt))

        # For non-GET requests, accept additional response codes indicating success
        # (but only if not expected statuses are not explicitly specified)
        # this is per HTTP spec:
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.5
        if 'expected_status' not in node.keys():
            if mytest.method == 'POST':
                mytest.expected_status = [200, 201, 204]
            elif mytest.method == 'PUT':
                mytest.expected_status = [200, 201, 204]
            elif mytest.method == 'DELETE':
                mytest.expected_status = [200, 202, 204]
            # Fallthrough default is simply [200]
        return mytest
