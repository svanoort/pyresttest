import logging
import json
import operator
import string
import parsing

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


VALIDATORS = {}
VALIDATOR_PARSE_FUNCTIONS = {}

# Binary comparison tests
COMPARATORS = {
    'lt': operator.lt,
    'less_than': operator.lt,
    'le': operator.lt,
    'less_than_or_equal': operator.lt,
    'eq': operator.eq,
    'equals': operator.eq,
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

def parse_validator(name, config_node):
    """ Parse a validator from configuration and use it """
    if name not in VALIDATORS:
        raise ValueError("Name {0} is not a named validator type!".format(name))
    return VALIDATOR_PARSE_FUNCTIONS[name].parse(config_node)

def register_validator(name, parse_function):
    """ Registers a validator for use by this library
        Name is the string name for validator

        Parse function does parse(config_node) and returns a validator function
        Validator functions have signature:
            validate(response_body, context=None) - context is a bindings.Context object

        Validators return true or false (optionally throw exceptions)
    """
    if name in VALIDATORS:
        raise Exception("Validator exists with this name: {0}".format(name))

    VALIDATORS.add(name)
    VALIDATOR_PARSE_FUNCTIONS[name] = parse_function

def parse_extractor(extractor_type, config):
    """ Convert extractor type and config to an extractor instance """
    parse = EXTRACTORS.get(extractor_type.lower())
    if not parse:
        raise ValueError("Extractor {0} is not a valid extractor type".format(extractor_type))
    return parse(config)

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


def _get_extract_fn(config_dict):
    """ Utility function, get an extract function for a single valid extractor name in config
        and error if more than one or none """
    extract = None
    extract_config = None
    for key, value in config_dict.items():
        if key in EXTRACTORS:
            if extract is not None:
                raise ValueError("Cannot have multiple extract functions defined for validator!")
            else:
                extract = key
                extract_config = value
    if extract:
        return EXTRACTORS[extract](extract_config)
    else:  # No valid extractor
        return None

def parse_comparator_validator(config):
    """ Create a validator that does an extract from body and applies a comparator,
        Then does comparison vs expected value
        Syntax sample:
          { jsonpath_mini: 'node.child',
            operator: 'eq',
            expected: 'myValue'
          }
    """

    config = parsing.lowercase_keys(parsing.flatten_dictionaries(config))

    # Extract functions are called by using defined extractor names
    extract_fn = _get_extract_fn(config)
    if extract_fn is None:
        raise ValueError("Extract function for comparison is not valid or not found!")

    try:
        comparator = config['comparator']
    except KeyError:
        raise ValueError("No comparator found in comparator validator config, one must be!")
    comparator = COMPARATORS[comparator.lower()]
    if not comparator:
        raise ValueError("Invalid comparator given!")

    try:
        expected = config['expected']
    except KeyError:
        raise ValueError("No expected value found in comparator validator config, one must be!")

    # Expected value can be another extractor query, or a single value, or a templated value
    expectedval = None
    expected_extract_fn = None
    is_expected_template = False

    if isinstance(expected, basestring) or isinstance(expected, (int, long, float, complex)):
        expectedval = expected
    elif isinstance(expected, dict):
        expected = lowercase_keys(expected)
        template = expected.get('template')
        if template:  # Templated string
            if not isinstance(template, string):
                raise ValueError("Can't template a comparator-validator unless template value is a string")
            is_expected_template = True
            expectedval = template
        else:  # Extractor to compare against
            expected_extract_fn =  _get_extract_fn(expected)
            if not expected_extract_fn:
                raise ValueError("Can't supply a non-template, non-extract dictionary to comparator-validator")

    # TOOD pull out the following into some sort of factor/composition function for testability?
    if expectedval and not is_expected_template:
        # Simple extract and value comparison
        def validate(body, context=None):
            extracted = extract_fn(body, context=context)
            return comparator(extracted, expectedval)
        return validate

    elif expectedval and is_expected_template:
        def validate(body, context=None):
            extracted = extract_fn(body, context=context)
            if context:
                expected = string.Template(expectedval).safe_substitute(context.get_values())
            else:
                expected = expectedval
            return comparator(extracted, expected)
        return validate
    elif not expected_extract_fn:
        raise Exception("No extract function given, expected is not a string, this should never happen!")
    else:  # Extractor function for expected value
        def validate(body, context=None):
            extracted = extract_fn(body, context=context)
            expected = expected_extract_fn(body, context=context)
            return comparator(extracted, expected)
        return validate


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