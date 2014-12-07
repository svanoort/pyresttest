import traceback
import json

import yaml
import jsonschema

import pyresttest.validators as validators
from pyresttest.binding import Context
from pyresttest.parsing import lowercase_keys
from pyresttest.contenthandling import ContentHandler

# TODO figure out package management for coupling with main module
# TODO test out autoloading and autoloading with install

class JsonSchemaValidator(validators.AbstractValidator):
    """ Json schema validator using the jsonschema library """
    schema = None

    def validate(self, body=None, context=None):
        schema_text = self.schema.get_content(context=context)
        schema = yaml.safe_load(schema_text)
        # TODO add caching of parsed schema

        try:
            # TODO try draft3/draft4 iter_errors - https://python-jsonschema.readthedocs.org/en/latest/validate/#jsonschema.IValidator.iter_errors
            jsonschema.validate(json.loads(body), schema)
            return True
        except jsonschema.exceptions.ValidationError, ve:
            trace = traceback.format_exc()
            return validators.Failure(message="JSON Schema Validation Failed", details=trace, validator=self, failure_type=validators.FAILURE_VALIDATOR_EXCEPTION)

    def get_readable_config(self, context=None):
        return "JSON schema validation"

    @classmethod
    def parse(cls, config):
        validator = JsonSchemaValidator()
        config = lowercase_keys(config)
        if 'schema' not in config:
            raise ValueError("Cannot create schema validator without a 'schema' configuration element!")
        validator.schema = ContentHandler.parse_content(config['schema'])
        return validator

VALIDATORS = {'json_schema': JsonSchemaValidator.parse}