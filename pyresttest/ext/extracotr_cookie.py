# coding=utf-8

import sys

import pyresttest.validators as validators
from pyresttest.binding import Context

# Python 3 compatibility
if sys.version_info[0] > 2:
    from past.builtins import basestring
from pyresttest.six import text_type
from pyresttest.six import binary_type

def _first(lst):
    if len(lst) > 0:
        return lst[0]
    return None


def _list_to_multi_value_map(lst):
    a_map = {}
    for k, v in lst:
        if k not in a_map:
            a_map[k] = v
        else:
            if isinstance(a_map[k], list):
                a_map[k].append(v)
            else:
                a_map[k] = [a_map[k], v]
    return a_map


class CookieExtractor(validators.AbstractExtractor):
    """get a wanted cookie"""

    extractor_type = 'cookie'
    is_body_extractor = True
    HEADER_NAME = 'Set-Cookie'

    @classmethod
    def parse(cls, config, extractor_base=None):
        base = CookieExtractor()
        return cls.configure_base(config, base)

    def extract_internal(self, query=None, args=None, body=None, headers=None):
        headers_map = _list_to_multi_value_map(headers)
        return _first([
            x for x in headers_map.get(CookieExtractor.HEADER_NAME.lower(), [])
            if ('%s=' % query) in x
        ])


EXTRACTORS = {'cookie': CookieExtractor.parse}
