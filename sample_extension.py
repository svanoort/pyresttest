# Sample python extension
import pyresttest.validators as validators
from pyresttest.binding import Context



class ContainsValidator(validators.AbstractValidator):
    # Sample validator that verifies a string is contained in the request body
    contains_string = None

    def validate(self, body, context=None):
        result = self.contains_string in body
        if result:
            return True
        else:  # Return failure object with additional information
            message = "Request body did not contain string: {0}".format(self.contains_string)
            return validators.ValidationFailure(message=message, details=None, validator=self)

    @staticmethod
    def parse(config):
        """ Parse a contains validator, which takes as the config a simple string to find """
        if not isinstance(config, basestring):
            raise TypeError("Contains input must be a simple string")
        validator = ContainsValidator()
        validator.contains_string = config
        return validator

def test_has_braces(input_string):
    """ Test if input string contains a brace ({}) """
    return '{' in input_string or '}' in input_string


def extract_weirdzo(body, context=None):
    """ Extractor function that always returns 'zorba' """
    return 'zorba'


def parse_extractor_weirdzo(config):
    """ Parser for extractor config that always ignores config
        and returns the extract_weirdzo function """
    return extract_weirdzo


# This is where the magic happens, each one of these is a registry of validators/extractors/generators to use
VALIDATORS = {'contains': ContainsValidator.parse}
VALIDATOR_TESTS = {'has_braces': test_has_braces}
# Converts to lowercase and tests for equality
VALIDATOR_COMPARATORS = {'str.eq.lower': lambda a,b: str(a).lower() == str(b).lower()}

EXTRACTORS = {'weirdzo': parse_extractor_weirdzo}