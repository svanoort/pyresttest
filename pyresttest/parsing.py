from __future__ import absolute_import
import sys
import string
import os
from optparse import OptionParser

# Python 3 compatibility shims
from . import six
from .six import binary_type
from .six import text_type

# Python 2/3 switches
PYTHON_MAJOR_VERSION = sys.version_info[0]
if PYTHON_MAJOR_VERSION > 2:
    from past.builtins import basestring

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

def parse_command_line_args(args_in):
    """ Runs everything needed to execute from the command line, so main method is callable without arg parsing """
    parser = OptionParser(
        usage="usage: %prog base_url test_filename.yaml [options] ")
    parser.add_option(u"--print-bodies", help="Print all response bodies",
                      action="store", type="string", dest="print_bodies")
    parser.add_option(u"--print-headers", help="Print all response headers",
                      action="store", type="string", dest="print_headers")
    parser.add_option(u"--log", help="Logging level",
                      action="store", type="string")
    parser.add_option(u"--interactive", help="Interactive mode",
                      action="store", type="string")
    parser.add_option(
        u"--url", help="Base URL to run tests against", action="store", type="string")
    parser.add_option(u"--test", help="Test file to use",
                      action="store", type="string")
    parser.add_option(u'--import_extensions',
                      help='Extensions to import, separated by semicolons', action="store", type="string")
    parser.add_option(
        u'--vars', help='Variables to set, as a YAML dictionary', action="store", type="string")
    parser.add_option(u'--verbose', help='Put cURL into verbose mode for extra debugging power',
                      action='store_true', default=False, dest="verbose")
    parser.add_option(u'--ssl-insecure', help='Disable cURL host and peer cert verification',
                      action='store_true', default=False, dest="ssl_insecure")
    parser.add_option(u'--absolute-urls', help='Enable absolute URLs in tests instead of relative paths',
                      action="store_true", dest="absolute_urls")
    parser.add_option(u'--skip_term_colors', help='Turn off the output term colors',
                      action='store_true', default=False, dest="skip_term_colors")
    parser.add_option(u'--junit', help='Path to junit file to write',
                      action='store', type="string")

    (args, unparsed_args) = parser.parse_args(args_in)
    args = vars(args)

    # Handle url/test as named, or, failing that, positional arguments
    if not args['url'] or not args['test']:
        if len(unparsed_args) == 2:
            args[u'url'] = unparsed_args[0]
            args[u'test'] = unparsed_args[1]
        elif len(unparsed_args) == 1 and args['url']:
            args['test'] = unparsed_args[0]
        elif len(unparsed_args) == 1 and args['test']:
            args['url'] = unparsed_args[0]
        else:
            parser.print_help()
            parser.error(
                "wrong number of arguments, need both url and test filename, either as 1st and 2nd parameters or via --url and --test")

    # So modules can be loaded from current folder
    args['cwd'] = os.path.realpath(os.path.abspath(os.getcwd()))
    return args
