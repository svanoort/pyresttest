# -*- coding: utf-8 -*-

# file sequence generator

import sys
import os

# Python 3 compatibility
if sys.version_info[0] > 2:
    from past.builtins import basestring


def factory_file_seq_generator(values):
    """ Returns generators that picks values from a certain file in sequence"""

    def file_seq_generator():
        with open(values, 'rU') as my_file:
            cnt_list = my_file.readlines()
            i = 0
            while(True):
                yield cnt_list[i].strip()
                if i == len(cnt_list):
                    i == 0
    return file_seq_generator

def parse_file_seq_generator(config):
    """ Parse file seq generator """
    vals = config['values']
    if not vals:
        raise ValueError('Values for choice filepath must exist')
    if not isinstance(vals, basestring):
        raise ValueError('Values must be a basestring')
    # with open(vals) as f:
    #     if not isinstance(f, file):
    #         raise ValueError('File opened from filepath is not valid')
    if not os.path.isfile(vals):
        raise ValueError('File opened from filepath is not valid')
    return factory_file_seq_generator(vals)()



# This is where the magic happens, each one of these is a registry of
# validators/extractors/generators to use
# VALIDATORS = {'contains': ContainsValidator.parse}
# VALIDATOR_TESTS = {'is_dict': test_is_dict}

# Converts to lowercase and tests for equality
# COMPARATORS = {'str.eq.lower': lambda a, b: str(a).lower() == str(b).lower()}

# EXTRACTORS = {'weirdzo': WeirdzoExtractor.parse}
GENERATORS = {'file_seq': parse_file_seq_generator}
