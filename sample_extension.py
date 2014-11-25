# Sample python extension
from pyresttest import validators
from pyresttest.binding import Context


class ContainsValidator(validators.AbstractValidator):
    # Sample validator that verifies a string is contained in the request body
    contains_string = None

    def validate(self, body, context=None):
        result = self.contains_string in body
        if result:
            return true
        else:  # Return failure object with additional information
            message = "Request body did not contain string: {0}".format(self.contains_string)
            return validators.ValidationFailure(message=message, details=None, validator=self)

    @staticmethod
    def parse(config):
        """ Parse a contains validator, which takes as the config a simple string to find """
        if isinstance(config, basestring):
            raise TypeError("Contains input must be a simple string")
        validator = ContainsValidator()
        validator.contains_string = config
        return validator

validators.register_validator('contains', ContainsValidator.parse)