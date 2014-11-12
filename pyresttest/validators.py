import logging
import json
import operator
import string
import parsing
import os

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
        - Uses TESTS, for pluggable test functions
    - comparator validator:
        - runs named extractor, compares to expected value (can be template or extractor)
        - uses (pluggable) comparator function for comparison

"""


VALIDATORS = dict()
# Includes 'comparator,'extracttest'
# Validators are registered once their parse functions exist

def safe_length(var):
    """ Exception-safe length check, returns -1 if no length on type or error """
    output = -1
    try:
        output = len(var)
    except:
        pass
    return output

# Binary comparison tests
COMPARATORS = {
    'count_eq': lambda x,y: safe_length(x) == y,
    'lt': operator.lt,
    'less_than': operator.lt,
    'le': operator.lt,
    'less_than_or_equal': operator.lt,
    'eq': operator.eq,
    'equals': operator.eq,
    'str_eq': lambda x,y: operator.eq(str(x), str(y)),
    'ne': operator.eq,
    'not_equals': operator.eq,
    'ge': operator.ge,
    'greater_than_or_equal': operator.ge,
    'gt': operator.gt,
    'greater_than': operator.gt,
    'contains': lambda x,y: x and y and operator.contains(x,y), # is y in x
    'contained_by': lambda x,y: x and y and operator.contains(y,x), # is x in y
}

# Unury comparison tests
TESTS = {
    'exists': lambda x: bool(x),
    'not_exists' : lambda x: not bool(x)
}

def parse_validator(name, config_node):
    '''Parse a validator from configuration and use it '''
    name = name.lower()
    if name not in VALIDATORS:
        raise ValueError("Name {0} is not a named validator type!".format(name))
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

        Validators return true or false and optionally can return a ValidationFailure instead of false
        This allows for passing more details
    '''
    name = name.lower()
    if name in VALIDATORS:
        raise Exception("Validator exists with this name: {0}".format(name))

    VALIDATORS[name] = parse_function

class ValidationFailure(object):
    """ Encapsulates why and how a validation failed for user consumption
        Message is a short explanation, details is a longer, multiline reason
        Validator is the validator that failed (for config info)
    """
    message = None
    details = None
    validator = None

    def __nonzero__(self):
        """ ValidationFailure objects test as False, simplifies coding with them """
        return False

    def __str__(self):
        return self.message

    def __init__(self, message="", details="", validator=None):
        self.message = message
        self.details = details
        self.validator = validator



class Extractor(object):
    """ Encapsulates extractor function in a readable format so people can understand
        what the parsed extract function should be doing """
    extractor_type = None  # Name
    config = None  # Settings info for printing, ONLY USED TO DISPLAY,
    extract_fn = None  # Actual extract function, does execution and is parsed already

    def config_string(self, context=None):
        """ Print a config string describing what comparator does, for detailed debugging
            Context is supplied so can show pre/post substitution
        """
        lines = list()
        lines.append("Extractor named: {0}".format(extractor_type))
        lines.append("Extractor config: {0}".format(config))
        return os.linesep.join(lines)  #Output lines joined by separator

    def __str__(self):
        return "Extractor type: {0} and config: {1}".format(self.extractor_type, self.config)

    def extract(self, body, context=None):
        return self.extract_fn(body, context=context)


class AbstractValidator(object):
    """ Encapsulates basic validator handling """
    name = None
    config = None

    def validate(self, body, context=None):
        """ Run the validation function, return true or a ValidationFailure """
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

    def validate(self, body, context=None):
        try :
            extracted_val = self.extractor.extract(body, context=context)
        except Exception as e:
            return ValidationFailure(message="Extractor threw exception", details=e, validator=self)

        # Compute expected output, either templating or using expected value
        expected_val = None
        if isinstance(self.expected, Extractor):
            try:
                expected_val = self.expected.extract(body, context=context)
            except Exception as e:
                return ValidationFailure(message="Expected value extractor threw exception", details=e, validator=self)
        elif self.isTemplateExpected and context:
            expected_val = string.Template(self.expected).safe_substitute(context.get_values())
        else:
            expected_val = self.expected

        comparison = self.comparator(extracted_val, expected_val)
        if not comparison:
            failure = ValidationFailure(validator=self)
            failure.message = "Comparison failed, evaluating {0}({1}, {2}) returned False".format(self.comparator_name, extracted_val, expected_val)
            failure.details = self.config
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
            raise ValueError("Extract function for comparison is not valid or not found!")

        try:
            output.comparator_name = config['comparator'].lower()
        except KeyError:
            raise ValueError("No comparator found in comparator validator config, one must be!")
        output.comparator = COMPARATORS[output.comparator_name]
        if not output.comparator:
            raise ValueError("Invalid comparator given!")

        try:
            expected = config['expected']
        except KeyError:
            raise ValueError("No expected value found in comparator validator config, one must be!")

        # Expected value can be another extractor query, or a single value, or a templated value

        if isinstance(expected, basestring) or isinstance(expected, (int, long, float, complex)):
            output.expected = expected
        elif isinstance(expected, dict):
            expected = parsing.lowercase_keys(expected)
            template = expected.get('template')
            if template:  # Templated string
                if not isinstance(template, basestring):
                    raise ValueError("Can't template a comparator-validator unless template value is a string")
                output.isTemplateExpected = True
                output.expected = template
            else:  # Extractor to compare against
                output.expected =  _get_extractor(expected)
                if not output.expected:
                    raise ValueError("Can't supply a non-template, non-extract dictionary to comparator-validator")

        return output

register_validator('comparator', ComparatorValidator.parse)
register_validator('compare', ComparatorValidator.parse)


class ExtractTestValidator(AbstractValidator):
    """ Does extract and test from request body """
    name = 'ExtractTestValidator'
    extractor = None
    test_fn = None
    test_name = None
    config = None

    @staticmethod
    def parse(config):
        output = ExtractTestValidator()
        config = parsing.lowercase_keys(parsing.flatten_dictionaries(config))
        output.config = config
        extractor = _get_extractor(config)
        output.extractor = extractor

        test_name = config['test']
        output.test_name = test_name
        test_fn = TESTS[test_name]
        output.test_fn = test_fn
        return output

    def validate(self, body, context=None):
        try:
            extracted = self.extractor.extract(body, context=context)
        except Exception as e:
            return ValidationFailure(message="Exception thrown while running extraction from body", details=e, validator=self)

        tested = self.test_fn(extracted)
        if tested:
            return True
        else:
            failure = ValidationFailure(details=self.config, validator=self)
            failure.message = "Extract and test validator failed on test: {0}({1})".format(self.test_name, extracted)
            return failure

register_validator('extract_test', ExtractTestValidator.parse)

def parse_extractor_minijson(config):
    """ Creates an extractor function using the mini-json query functionality """
    if isinstance(config, dict):
        try:
            config = config['template']
            isTemplate = True
        except KeyError:
            raise ValueError("Cannot define a dictionary config for mini-json extractor without it having template key")
    elif isinstance(config, basestring):
        isTemplate = False
    else:
        raise TypeError("Mini-json extractor must have a string or {template: querystring} configuration node!")

    # Closure: config information is closed over in scope
    def extract(body, context=None):
        try:
            body = json.loads(body)
        except ValueError:
            raise ValueError("Not legal JSON!")
        return query_dictionary(config, body, context=context, isTemplate=isTemplate)

    return extract

# Extractor parse functions
EXTRACTORS = {
    'jsonpath_mini': parse_extractor_minijson
    # ENHANCEME: add JsonPath-rw support for full JsonPath syntax
    # ENHANCEME: add elementree support for xpath extract on XML, very simple no?
    #  See: https://docs.python.org/2/library/xml.etree.elementtree.html, findall syntax
}

def parse_extractor(extractor_type, config):
    """ Convert extractor type and config to an extractor instance
        Uses registered parse function for that extractor type
        Parse functions may return either:
            - An extraction function (wrapped in an Extractor instance with configs and returned)
            - OR a a full Extractor instance (configured)
    """
    parse = EXTRACTORS.get(extractor_type.lower())
    if not parse:
        raise ValueError("Extractor {0} is not a valid extractor type".format(extractor_type))
    parsed = parse(config)

    if isinstance(parsed, Extractor):  # Parser gave a full extractor
        return parsed
    elif callable(parsed):  # Create an extractor using returned extraction function
        extractor = Extractor()
        extractor.extractor_type = extractor_type
        extractor.config = config
        extractor.extract_fn = parsed
        return extractor
    else:
        raise TypeError("Parsing functions for extractors must return either an extraction function or an Extractor instance!")


def register_extractor(extractor_name, parse_function):
    """ Register a new body extraction function """
    if not isinstance(extractor_name, basestring):
        raise TypeError("Cannot register a non-string extractor name")
    if extractor_name.lower() == 'comparator':
        raise ValueError("Cannot register extractors called 'comparator', that is a reserved name")
    elif extractor_name.lower() == 'test':
        raise ValueError("Cannot register extractors called 'test', that is a reserved name")
    elif extractor_name.lower() == 'expected':
        raise ValueError("Cannot register extractors called 'expected', that is a reserved name")
    elif extractor_name in EXTRACTORS:
        raise ValueError("Cannot register an extractor name that already exists: {0}".format(extractor_name))
    EXTRACTORS[extractor_name] = parse_function


def _get_extractor(config_dict):
    """ Utility function, get an extract function for a single valid extractor name in config
        and error if more than one or none """
    extractor = None
    extract_config = None
    for key, value in config_dict.items():
        if key in EXTRACTORS:
            return parse_extractor(key, value)
    else:  # No valid extractor
        return None


def query_dictionary(query, dictionary, delimiter='.', context=None, isTemplate=False):
    """ Do an xpath-like query with dictionary, using a template if relevant """
    # Based on http://stackoverflow.com/questions/7320319/xpath-like-query-for-nested-python-dictionaries

    if isTemplate and context:
        query = string.Template(query).safe_substitute(context.get_values())
    try:
        for x in query.strip(delimiter).split(delimiter):
            try:
                x = int(x)
                dictionary = dictionary[x]
            except ValueError:
                dictionary = dictionary[x]
    except:
        return None
    return dictionary