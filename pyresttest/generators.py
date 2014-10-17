import random
import string
import os

from parsing import flatten_dictionaries, lowercase_keys, safe_to_bool
import parsing

""" Collection of generators to be used in templating for test data

Plans: extend these by allowing generators that take generators for input
Example: generators that case-swap
"""

INT32_MAX_VALUE = 2147483647  # Max of 32 bit unsigned int

def factory_generate_ids(starting_id=1, increment=1):
    """ Return function generator for ids starting at starting_id
        Note: needs to be called with () to make generator """
    def generate_started_ids():
        val = starting_id
        local_increment = increment
        while(True):
            yield val
            val += local_increment
    return generate_started_ids

def generator_basic_ids():
    """ Return ids generator starting at 1 """
    return factory_generate_ids(1)()

def generator_random_int32():
    """ Random integer generator for up to 32-bit signed ints """
    rand = random.Random()
    while (True):
        yield random.randint(0, INT32_MAX_VALUE)

def factory_generate_text(legal_characters=string.ascii_letters, length=8):
    """ Returns a generator function for text with given legal_characters string and length
        Default is ascii letters, length 8

        For hex digits, combine with string.hexstring, etc
        """
    def generate_text():
        my_len = length
        rand = random.Random()
        while(True):
            array = [random.choice(legal_characters) for x in xrange(0, my_len)]
            yield ''.join(array)

    return generate_text


def factory_env_variable(env_variable):
    """ Return a generator function that reads from an environment variable """

    def return_variable():
        variable_name = env_variable
        while(True):
            yield os.environ.get(variable_name)

    return return_variable

def factory_env_string(env_string):
    """ Return a generator function that uses OS expand path to expand environment variables in string """

    def return_variable():
        my_input = env_string
        while(True):
            yield os.path.expandvars(my_input)



class GeneratorFactory:
    """ Implements the parsing logic for YAML, and acts as single point for reading configuration """

    # List generators and supply a parsing function if needed
    GENERATOR_TYPES = {
        'env_variable' : None,
        'env_string' : None,
        'count_numbers' : None,
        'rand_int' : None
    }


    """ Builds generators from configuration elements """
    def parse(configuration):
        """ Parses a configuration built from yaml and returns a generator
            Configuration should be a map
        """

        configuration = resttest.lowercase_keys(resttest.flatten_dictionaries(configuration))
        gen_type = str(configuration.get(u'type'))
        parse_function = GENERATOR_TYPES.get(gen_type)

        if gen_type not in GENERATOR_TYPES:
            raise ValueError('Generator type given {0} is not valid '.format(gen_type))
        elif parse_function:
            return parse_function(configuration)

        # Do the easy parsing
        if gen_type == u'env_variable':
            return factory_env_variable(configuration[u'variable_name'])
        elif gen_type == u'env_string':
            return factory_env_string(configuration[u'string'])
        elif gen_type == u'count_numbers':
            start = configuration.get('start')
            increment = configuration.get('increment')
            if not start:
                start = 1
            if not end:
                increment = 1
            return factory_generate_ids(start, increment)
        elif gen_type == u'rand_int':
            return generator_random_int32()
