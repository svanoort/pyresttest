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

class WeirdzoExtractor(validators.AbstractExtractor):
    """ Always returns 'zorba' """

    extractor_type = 'weirdzo'
    is_body_extractor = True

    @classmethod
    def parse(cls, config, extractor_base=None):
        base = WeirdzoExtractor()
        return cls.configure_base(config, base)

    def extract_internal(self, query=None, args=None, body=None, headers=None):
        return 'zorba'

def parse_generator_doubling(config):
    """ Returns generators that double with each value returned, config includes start value """
    start = 1
    if 'start' in config:
        start = int(config['start'])

    # We cannot simply use start as the variable, because of scoping limitations
    def generator():
        val = start
        while(True):
            yield val
            val = val*2
    return generator()

def test_is_dict(input):
    """ Simple test that returns true if item is a dictionary """
    return isinstance(input, dict)

# This is where the magic happens, each one of these is a registry of validators/extractors/generators to use
VALIDATORS = {'contains': ContainsValidator.parse}
VALIDATOR_TESTS = {'is_dict': test_is_dict}

# Converts to lowercase and tests for equality
COMPARATORS = {'str.eq.lower': lambda a,b: str(a).lower() == str(b).lower()}

EXTRACTORS = {'weirdzo': WeirdzoExtractor.parse}
GENERATORS = {'doubling': parse_generator_doubling}