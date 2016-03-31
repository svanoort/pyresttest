import logging
import json
import Cookie
import operator
import traceback
import string
import os
import re
import sys

# Local module imports
from . import parsing

# Python 3 compatibility shims
from . import six
from .six import binary_type
from .six import text_type

# Python 3 compatibility
PYTHON_MAJOR_VERSION = sys.version_info[0]
if PYTHON_MAJOR_VERSION > 2:
    from past.builtins import basestring
    from past.builtins import long

"""
Validator/Extractor logic for utility use
Defines objects:
- Extractors that take a text body and context, and return a result from the (text) body
- Validators (functions) that take a text body and context, and validate the body
- Several useful implementations for each:

Extractors:
    - json mini extractor (sudo-jsonpath)

Validators:
    - TEST validator, config includes and extractor function and test name, applies test to extract results
        - Uses VALIDATOR_TESTS, for pluggable test functions
    - comparator validator:
        - runs named extractor, compares to expected value (can be template or extractor)
        - uses (pluggable) comparator function for comparison

"""

logger = logging.getLogger('pyresttest.validators')


# Binary comparison tests
COMPARATORS = {
    'count_eq': lambda x, y: safe_length(x) == y,
    'lt': operator.lt,
    'less_than': operator.lt,
    'le': operator.lt,
    'less_than_or_equal': operator.lt,
    'eq': operator.eq,
    'equals': operator.eq,
    'str_eq': lambda x, y: operator.eq(str(x), str(y)),
    'ne': operator.ne,
    'not_equals': operator.ne,
    'ge': operator.ge,
    'greater_than_or_equal': operator.ge,
    'gt': operator.gt,
    'greater_than': operator.gt,
    'contains': lambda x, y: x and operator.contains(x, y),  # is y in x
    'contained_by': lambda x, y: y and operator.contains(y, x),  # is x in y
    'regex': lambda x, y: regex_compare(str(x), str(y)),
    'type': lambda x, y: test_type(x, y)
}
COMPARATORS['length_eq'] = COMPARATORS['count_eq']

# Allow for testing basic types in comparators
TYPES = {
    'null': type(None),
    'none': type(None),
    'number': (int, long, float),
    'int': (int, long),
    'float': float,
    'boolean': bool,
    'string': basestring,
    'array': list,
    'list': list,
    'dict': dict,
    'map': dict,
    'scalar': (bool, int, long, float, basestring, type(None)),
    'collection': (list, dict, set)
}


def test_type(val, mytype):
    """ Check value fits one of the types, if so return true, else false """

    typelist = TYPES.get(mytype.lower())

    if typelist is None:
        raise TypeError(
            "Type {0} is not a valid type to test against!".format(mytype.lower()))
    try:
        for testtype in typelist:
            if isinstance(val, testtype):
                return True
        return False
    except TypeError:
        return isinstance(val, typelist)

# Unury comparison tests
VALIDATOR_TESTS = {
    'exists': lambda x: x is not None,
    'not_exists': lambda x: x is None
}

# Validators and Extractors are registered once their parse functions exist
EXTRACTORS = dict()
VALIDATORS = dict()


def safe_length(var):
    """ Exception-safe length check, returns -1 if no length on type or error """
    output = -1
    try:
        output = len(var)
    except:
        pass
    return output


def regex_compare(input, regex):
    return bool(re.search(regex, input))

# Validator Failure Reasons
FAILURE_INVALID_RESPONSE = 'Invalid HTTP Response Code'
FAILURE_CURL_EXCEPTION = 'Curl Exception'
FAILURE_TEST_EXCEPTION = 'Test Execution Exception'
FAILURE_VALIDATOR_FAILED = 'Validator Failed'
FAILURE_VALIDATOR_EXCEPTION = 'Validator Exception'
FAILURE_EXTRACTOR_EXCEPTION = 'Extractor Exception'


class Failure(object):
    """ Encapsulates why and how a validation failed for user consumption
        Message is a short explanation, details is a longer, multiline reason
        Validator is the validator that failed (for config info)
    """
    message = None
    failure_type = None
    details = None
    validator = None

    def __nonzero__(self):
        """ Failure objects test as False, simplifies coding with them """
        return False

    def __bool__(self):
        """ Failure objects test as False, simplifies coding with them """
        return False

    def __str__(self):
        return self.message

    def __init__(self, message="", details="", failure_type=None, validator=None):
        self.message = message
        self.details = details
        self.validator = validator
        self.failure_type = failure_type


class AbstractExtractor(object):
    """ Basic extractor, you only need to implement full_extract """

    extractor_type = None
    query = None
    is_templated = False
    is_body_extractor = False  # Uses response body
    is_header_extractor = False  # Uses response headers
    args = None

    def __str__(self):
        return "Extractor type: {0}, query: {1}, is_templated: {2}, args: {3}".format(self.extractor_type, self.query, self.is_templated, self.args)

    def extract_internal(self, query=None, body=None, headers=None, args=None):
        """ Do extraction, query should be pre-templated """
        pass

    def extract(self, body=None, headers=None, context=None):
        """ Extract data """
        query = self.templated_query(context=context)
        args = self.args
        return self.extract_internal(query=query, body=body, headers=headers, args=self.args)

    def templated_query(self, context=None):
        query = self.query
        if context and self.is_templated:
            query = string.Template(query).safe_substitute(
                context.get_values())
        return query

    def get_readable_config(self, context=None):
        """ Print a human-readable version of the configuration """
        query = self.templated_query(context=context)
        output = 'Extractor Type: {0},  Query: "{1}", Templated?: {2}'.format(
            self.extractor_type, query, self.is_templated)
        args_string = None
        if self.args:
            args_string = ", Args: " + str(self.args)
            output = output + args_string
        return output

    @classmethod
    def configure_base(cls, config, extractor_base):
        """ Parse config object and do basic config on an Extractor
        """

        if isinstance(config, dict):
            try:
                config = config['template']
                extractor_base.is_templated = True
                extractor_base.query = config
            except KeyError:
                raise ValueError(
                    "Cannot define a dictionary config for abstract extractor without it having template key")
        elif isinstance(config, basestring):
            extractor_base.query = config
            extractor_base.is_templated = False
        else:
            raise TypeError(
                "Base extractor must have a string or {template: querystring} configuration node!")
        return extractor_base


class MiniJsonExtractor(AbstractExtractor):
    """ Extractor that uses jsonpath_mini syntax
        IE key.key or array_index.key extraction
    """
    extractor_type = 'jsonpath_mini'
    is_body_extractor = True

    def extract_internal(self, query=None, args=None, body=None, headers=None):
        if PYTHON_MAJOR_VERSION > 2 and isinstance(body, binary_type):
            body = text_type(body, 'utf-8')  # Default JSON encoding

        try:
            body = json.loads(body)
            return self.query_dictionary(query, body)
        except ValueError:
            raise ValueError("Not legal JSON!")

    @staticmethod
    def query_dictionary(query, dictionary, delimiter='.'):
        """ Do an xpath-like query with dictionary, using a template if relevant """
        # Based on
        # http://stackoverflow.com/questions/7320319/xpath-like-query-for-nested-python-dictionaries

        try:
            stripped_query = query.strip(delimiter)
            if stripped_query:
                for x in stripped_query.split(delimiter):
                    try:
                        x = int(x)
                        dictionary = dictionary[x]
                    except ValueError:
                        dictionary = dictionary[x]
        except:
            return None
        return dictionary

    @classmethod
    def parse(cls, config):
        base = MiniJsonExtractor()
        return cls.configure_base(config, base)
        return base


class HeaderExtractor(AbstractExtractor):
    """ Extractor that pulls out a named header value... or list of values if multiple values defined """
    extractor_type = 'header'
    is_header_extractor = True

    def extract_internal(self, query=None, args=None, body=None, headers=None):
        low = query.lower()
        # Value for all matching key names
        extracted = [y[1] for y in filter(lambda x: x[0] == low, headers)]
        if len(extracted) == 0:
            raise ValueError("Invalid header name {0}".format(query))
        elif len(extracted) == 1:
            return extracted[0]
        else:
            return extracted

    @classmethod
    def parse(cls, config, extractor_base=None):
        base = HeaderExtractor()
        return cls.configure_base(config, base)


class CookieExtractor(AbstractExtractor):
    """ Extractor that pulls out a named cookie """
    extractor_type = 'cookie'
    is_header_extractor = True

    def extract_internal(self, query = None, args = None, body = None, headers = None):
        extracted = [y[1] for y in filter(lambda x: x[0] == 'set-cookie', headers) if y[1].startswith(query + '=')]
        if len(extracted) == 0:
            raise ValueError("Cookie named {0} not known".format(query))
        else:
            return Cookie.SimpleCookie(extracted[-1])[query].value

    @classmethod
    def parse(cls, config, extractor_base = None):
        base = CookieExtractor()
        return cls.configure_base(config, base)


class RawBodyExtractor(AbstractExtractor):
    """ Extractor that returns the full request body """
    extractor_type = 'raw_body'
    is_header_extractor = False
    is_body_extractor = True

    def extract_internal(self, query=None, args=None, body=None, headers=None):
        return body

    @classmethod
    def parse(cls, config, extractor_base=None):
        # Doesn't take any real configuration
        base = RawBodyExtractor()
        return base


def _get_extractor(config_dict):
    """ Utility function, get an extract function for a single valid extractor name in config
        and error if more than one or none """
    extractor = None
    extract_config = None
    for key, value in config_dict.items():
        if key in EXTRACTORS:
            return parse_extractor(key, value)
    else:  # No valid extractor
        raise Exception(
            'No valid extractor name to use in input: {0}'.format(config_dict))


class AbstractValidator(object):
    """ Encapsulates basic validator handling """
    name = None
    config = None

    def validate(self, body=None, headers=None, context=None):
        """ Run the validation function, return true or a Failure """
        pass


class ComparatorValidator(AbstractValidator):
    """ Does extract and compare from request body   """

    name = 'ComparatorValidator'
    config = None   # Configuration text, if parsed
    extractor = None
    comparator = None
    comparator_name = ""
    expected = None
    isTemplateExpected = False

    def get_readable_config(self, context=None):
        """ Get a human-readable config string """
        string_frags = list()
        string_frags.append(
            "Extractor: " + self.extractor.get_readable_config(context=context))
        if isinstance(self.expected, AbstractExtractor):
            string_frags.append("Expected value extractor: " +
                                self.expected.get_readable_config(context=context))
        elif self.isTemplateExpected:
            string_frags.append(
                'Expected is templated, raw value: {0}'.format(self.expected))
        return os.linesep.join(string_frags)

    def validate(self, body=None, headers=None, context=None):
        try:
            extracted_val = self.extractor.extract(
                body=body, headers=headers, context=context)
        except Exception as e:
            trace = traceback.format_exc()
            return Failure(message="Extractor threw exception", details=trace, validator=self, failure_type=FAILURE_EXTRACTOR_EXCEPTION)

        # Compute expected output, either templating or using expected value
        expected_val = None
        if isinstance(self.expected, AbstractExtractor):
            try:
                expected_val = self.expected.extract(
                    body=body, headers=headers, context=context)
            except Exception as e:
                trace = traceback.format_exc()
                return Failure(message="Expected value extractor threw exception", details=trace, validator=self, failure_type=FAILURE_EXTRACTOR_EXCEPTION)
        elif self.isTemplateExpected and context:
            expected_val = string.Template(
                self.expected).safe_substitute(context.get_values())
        else:
            expected_val = self.expected

        # Handle a bytes-based body and a unicode expected value seamlessly
        if isinstance(extracted_val, binary_type) and isinstance(expected_val, text_type):
            expected_val = expected_val.encode('utf-8')
        comparison = self.comparator(extracted_val, expected_val)

        if not comparison:
            failure = Failure(validator=self)
            failure.message = "Comparison failed, evaluating {0}({1}, {2}) returned False".format(
                self.comparator_name, extracted_val, expected_val)
            failure.details = self.get_readable_config(context=context)
            failure.failure_type = FAILURE_VALIDATOR_FAILED
            return failure
        else:
            return True

    @staticmethod
    def parse(config):
        """ Create a validator that does an extract from body and applies a comparator,
            Then does comparison vs expected value
            Syntax sample:
              { jsonpath_mini: 'node.child',
                operator: 'eq',
                expected: 'myValue'
              }
        """

        output = ComparatorValidator()
        config = parsing.lowercase_keys(parsing.flatten_dictionaries(config))
        output.config = config

        # Extract functions are called by using defined extractor names
        output.extractor = _get_extractor(config)

        if output.extractor is None:
            raise ValueError(
                "Extract function for comparison is not valid or not found!")

        if 'comparator' not in config:  # Equals comparator if unspecified
            output.comparator_name = 'eq'
        else:
            output.comparator_name = config['comparator'].lower()
        output.comparator = COMPARATORS[output.comparator_name]
        if not output.comparator:
            raise ValueError("Invalid comparator given!")

        try:
            expected = config['expected']
        except KeyError:
            raise ValueError(
                "No expected value found in comparator validator config, one must be!")

        # Expected value can be another extractor query, or a single value, or
        # a templated value

        if isinstance(expected, basestring) or isinstance(expected, (int, long, float, complex)):
            output.expected = expected
        elif isinstance(expected, dict):
            expected = parsing.lowercase_keys(expected)
            template = expected.get('template')
            if template:  # Templated string
                if not isinstance(template, basestring):
                    raise ValueError(
                        "Can't template a comparator-validator unless template value is a string")
                output.isTemplateExpected = True
                output.expected = template
            else:  # Extractor to compare against
                output.expected = _get_extractor(expected)
                if not output.expected:
                    raise ValueError(
                        "Can't supply a non-template, non-extract dictionary to comparator-validator")

        return output


class ExtractTestValidator(AbstractValidator):
    """ Does extract and test from request body """
    name = 'ExtractTestValidator'
    extractor = None
    test_fn = None
    test_name = None
    config = None

    def get_readable_config(self, context=None):
        """ Get a human-readable config string """
        return "Extractor: " + self.extractor.get_readable_config(context=context)

    @staticmethod
    def parse(config):
        output = ExtractTestValidator()
        config = parsing.lowercase_keys(parsing.flatten_dictionaries(config))
        output.config = config
        extractor = _get_extractor(config)
        output.extractor = extractor

        test_name = config['test']
        output.test_name = test_name
        test_fn = VALIDATOR_TESTS[test_name]
        output.test_fn = test_fn
        return output

    def validate(self, body=None, headers=None, context=None):
        try:
            extracted = self.extractor.extract(
                body=body, headers=headers, context=context)
        except Exception as e:
            trace = traceback.format_exc()
            return Failure(message="Exception thrown while running extraction from body", details=trace, validator=self, failure_type=FAILURE_EXTRACTOR_EXCEPTION)

        tested = self.test_fn(extracted)
        if tested:
            return True
        else:
            failure = Failure(details=self.get_readable_config(
                context=context), validator=self, failure_type=FAILURE_VALIDATOR_FAILED)
            failure.message = "Extract and test validator failed on test: {0}({1})".format(
                self.test_name, extracted)
            # TODO can we do better with details?
            return failure


def parse_extractor(extractor_type, config):
    """ Convert extractor type and config to an extractor instance
        Uses registered parse function for that extractor type
        Parse functions may return either:
            - An extraction function (wrapped in an Extractor instance with configs and returned)
            - OR a a full Extractor instance (configured)
    """
    parse = EXTRACTORS.get(extractor_type.lower())
    if not parse:
        raise ValueError(
            "Extractor {0} is not a valid extractor type".format(extractor_type))
    parsed = parse(config)

    if isinstance(parsed, AbstractExtractor):  # Parser gave a full extractor
        return parsed

    # Look for matching attributes... simple inheritance has issues because of
    # cross-module loading
    items = AbstractExtractor().__dict__
    if set(parsed.__dict__.keys()).issuperset(set(items.keys())):
        return parsed
    else:
        raise TypeError(
            "Parsing functions for extractors must return an AbstractExtractor instance!")


def parse_validator(name, config_node):
    '''Parse a validator from configuration and use it '''
    name = name.lower()
    if name not in VALIDATORS:
        raise ValueError(
            "Name {0} is not a named validator type!".format(name))
    valid = VALIDATORS[name](config_node)

    if valid.name is None:  # Carry over validator name if none set in parser
        valid.name = name
    if valid.config is None:  # Store config info if absent
        valid.config = config_node
    return valid


def register_validator(name, parse_function):
    ''' Registers a validator for use by this library
        Name is the string name for validator

        Parse function does parse(config_node) and returns a Validator object
        Validator functions have signature:
            validate(response_body, context=None) - context is a bindings.Context object

        Validators return true or false and optionally can return a Failure instead of false
        This allows for passing more details
    '''
    name = name.lower()
    if name in VALIDATORS:
        raise Exception("Validator exists with this name: {0}".format(name))

    VALIDATORS[name] = parse_function


def register_extractor(extractor_name, parse_function):
    """ Register a new body extraction function """
    if not isinstance(extractor_name, basestring):
        raise TypeError("Cannot register a non-string extractor name")
    if extractor_name.lower() == 'comparator':
        raise ValueError(
            "Cannot register extractors called 'comparator', that is a reserved name")
    elif extractor_name.lower() == 'test':
        raise ValueError(
            "Cannot register extractors called 'test', that is a reserved name")
    elif extractor_name.lower() == 'expected':
        raise ValueError(
            "Cannot register extractors called 'expected', that is a reserved name")
    elif extractor_name in EXTRACTORS:
        raise ValueError(
            "Cannot register an extractor name that already exists: {0}".format(extractor_name))
    EXTRACTORS[extractor_name] = parse_function


def register_test(test_name, test_function):
    """ Register a new one-argument test function """
    if not isinstance(test_name, basestring):
        raise TypeError("Cannot register a non-string test name")
    elif test_name in VALIDATOR_TESTS:
        raise ValueError(
            "Cannot register a test name that already exists: {0}".format(test_name))
    VALIDATOR_TESTS[test_name] = test_function


def register_comparator(comparator_name, comparator_function):
    """ Register a new twpo-argument comparator function returning true or false """
    if not isinstance(comparator_name, basestring):
        raise TypeError("Cannot register a non-string comparator name")
    elif comparator_name in COMPARATORS:
        raise ValueError(
            "Cannot register a comparator name that already exists: {0}".format(comparator_name))
    COMPARATORS[comparator_name] = comparator_function

# --- REGISTRY OF EXTRACTORS AND VALIDATORS ---
register_extractor('jsonpath_mini', MiniJsonExtractor.parse)
register_extractor('header', HeaderExtractor.parse)
register_extractor('cookie', CookieExtractor.parse)
register_extractor('raw_body', RawBodyExtractor.parse)
# ENHANCEME: add JsonPath-rw support for full JsonPath syntax
# ENHANCEME: add elementree support for xpath extract on XML, very simple no?
# See: https://docs.python.org/2/library/xml.etree.elementtree.html,
# findall syntax

register_validator('comparator', ComparatorValidator.parse)
register_validator('compare', ComparatorValidator.parse)
register_validator('assertEqual', ComparatorValidator.parse)
register_validator('extract_test', ExtractTestValidator.parse)
register_validator('assertTrue', ExtractTestValidator.parse)
