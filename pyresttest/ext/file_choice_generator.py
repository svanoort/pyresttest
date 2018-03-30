# -*- coding: utf-8 -*-

# file choice generator

import random
import linecache
import sys

# Python 3 compatibility
if sys.version_info[0] > 2:
    from past.builtins import basestring


def factory_file_choice_generator(values):
    """ Returns generators that picks values from a certain file"""

    def file_choice_generator():
        with open(values, 'rU') as my_file:
            cnt_list = my_file.readlines()  #list+choice的方式,如果读取文件较大,可能会导致list占用较多内不能,优化可改成yield计算count
            # count = len(my_file.readlines())
            if len(cnt_list) == 0:
                raise ValueError('The length of file %s is null' %(values))
            while(True):
                # cnt = linecache.getline(my_file, rand)
                yield random.choice(cnt_list).strip()
    return file_choice_generator

def parse_file_choice_generator(config):
    """ Parse file choice generator """
    vals = config['values']
    if not vals:
        raise ValueError('Values for choice filepath must exist')
    if not isinstance(vals, basestring):
        raise ValueError('Values must be a basestring')
    with open(vals) as f:
        if not isinstance(f, file):
            raise ValueError('File opened from filepath is not valid')
    return factory_file_choice_generator(vals)()



# This is where the magic happens, each one of these is a registry of
# validators/extractors/generators to use
# VALIDATORS = {'contains': ContainsValidator.parse}
# VALIDATOR_TESTS = {'is_dict': test_is_dict}

# Converts to lowercase and tests for equality
# COMPARATORS = {'str.eq.lower': lambda a, b: str(a).lower() == str(b).lower()}

# EXTRACTORS = {'weirdzo': WeirdzoExtractor.parse}
GENERATORS = {'file_choice': parse_file_choice_generator}
