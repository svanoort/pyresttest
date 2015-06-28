"""
Parsing utilities, pulled out so they can be used in multiple modules
"""

def resolve_variable(variable_name, scopes, default=None):
    """ Look for the first case in which variable is set in a list of scopes """
    if not scopes:
        return default
    for s in scopes:
        val = s.get(variable_name)
        if val is not None:
            return val
    return default


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
    else: #Not a list of dictionaries
        output = input;
    return output

def lowercase_keys(input_dict):
    """ Take input and if a dictionary, return version with keys all lowercase """
    if not isinstance(input_dict,dict):
        return input_dict

    safe = dict()
    for key,value in input_dict.items():
        safe[str(key).lower()] = value
    return safe

def safe_to_bool(input):
    """ Safely convert user input to a boolean, throwing exception if not boolean or boolean-appropriate string
      For flexibility, we allow case insensitive string matching to false/true values
      If it's not a boolean or string that matches 'false' or 'true' when ignoring case, throws an exception """
    if isinstance(input,bool):
        return input
    elif isinstance(input,unicode) or isinstance(input,str) and unicode(input,'UTF-8').lower() == u'false':
        return False
    elif isinstance(input,unicode) or isinstance(input,str) and unicode(input,'UTF-8').lower() == u'true':
        return True
    else:
        raise TypeError('Input Object is not a boolean or string form of boolean!')