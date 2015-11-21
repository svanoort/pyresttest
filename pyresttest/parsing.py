import sys
import string

# Python 3 compatibility shims
from six import binary_type
from six import text_type
PYTHON_MAJOR_VERSION = sys.version_info[0]

"""
Parsing utilities, pulled out so they can be used in multiple modules
"""

def encode_unicode_bytes(my_string):
    """ Shim function, converts Unicode to UTF-8 encoded bytes regardless of the source format
        Intended for python 3 compatibility mode, and b/c PyCurl only takes raw bytes
    """
    if not isinstance(my_string, basestring):
        my_string = repr(my_string)

    # TODO refactor this to use six types
    if PYTHON_MAJOR_VERSION == 2:
        if isinstance(my_string, str):
            return my_string
        elif isinstance(my_string, unicode):
            return my_string.encode('utf-8')
    else:
        if isinstance(my_string, str):
            return my_string.encode('utf-8')
        elif isinstance(my_string, bytes):
            return my_string

# TODO create a full class that extends string.Template
def safe_substitute_unicode_template(templated_string, variable_map):
    """ Perform string.Template safe_substitute on unicode input with unicode variable values by using escapes
        Catch: cannot accept unicode variable names, just values
        Returns a Unicode type output, if you want UTF-8 bytes, do encode_unicode_bytes on it
    """

    if PYTHON_MAJOR_VERSION > 2:  # Python 3 handles unicode templating natively, yay!
        return string.Template(templated_string).safe_substitute(variable_map)

    my_template = string.Template(encode_unicode_bytes(templated_string))
    my_escaped_dict = dict(map(lambda x: (x[0], encode_unicode_bytes(x[1])), variable_map.items()))
    templated = my_template.safe_substitute(my_escaped_dict)
    return text_type(templated, 'utf-8')

def safe_to_json(in_obj):
    """ Safely get dict from object if present for json dumping """
    if isinstance(in_obj, bytearray):
        return str(in_obj)
    if hasattr(in_obj, '__dict__'):
        return in_obj.__dict__
    try:
        return str(in_obj)
    except:
        return repr(in_obj)


def flatten_dictionaries(input):
    """ Flatten a list of dictionaries into a single dictionary, to allow flexible YAML use
      Dictionary comprehensions can do this, but would like to allow for pre-Python 2.7 use
      If input isn't a list, just return it.... """
    output = dict()
    if isinstance(input, list):
        for map in input:
            output.update(map)
    else:  # Not a list of dictionaries
        output = input
    return output


def lowercase_keys(input_dict):
    """ Take input and if a dictionary, return version with keys all lowercase and cast to str """
    if not isinstance(input_dict, dict):
        return input_dict
    safe = dict()
    for key, value in input_dict.items():
        safe[str(key).lower()] = value
    return safe


def safe_to_bool(input):
    """ Safely convert user input to a boolean, throwing exception if not boolean or boolean-appropriate string
      For flexibility, we allow case insensitive string matching to false/true values
      If it's not a boolean or string that matches 'false' or 'true' when ignoring case, throws an exception """
    if isinstance(input, bool):
        return input
    elif isinstance(input, basestring) and input.lower() == u'false':
        return False
    elif isinstance(input, basestring) and input.lower() == u'true':
        return True
    else:
        raise TypeError(
            'Input Object is not a boolean or string form of boolean!')


class SuperConfigurator(object):
    """ It's a bird!  It's a plane! No, it's....
        The solution to handling horribly nasty, thorny configuration handling methods

    """

    def run_configure(self, key, value, configurable, validator_func=None, converter_func=None, store_func=None, *args, **kwargs):
        """ Run a single configuration element
            Run a validator on the value, if supplied
            Run a converter_funct to turn the value into something to storeable:
                converter_func takes params (value) at least and throws exception if failed
            If a  store_func is supplied, use that to store the option
              store_func needs to take params (object, key, value, args, kwargs)
            If store_func NOT supplied we do a setattr on object
        """
        if validator_func and not validator(value):
            raise TypeError("Illegal argument for {0}".format(value))
        storeable = value
        if converter_func:
            storeable = converter_func(value)
        if store_func:
            store_func(configurable, key, storeable)
        else:
            configurable.setattr(configurable, key, value)

    def configure(self, configs, configurable, handler, *args, **kwargs):
        """ Use the configs and configurable to parse"""
        for key, value in configs.items():
            # Read handler arguments and use them to call the configurator
            handler[key] = config_options
            self.run_configure(value, configurable)
