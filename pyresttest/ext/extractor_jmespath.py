import traceback
import json
import sys
PYTHON_MAJOR_VERSION = sys.version_info[0]

import yaml
import ast
import jmespath

try:  # First try to load pyresttest from global namespace
    from pyresttest import validators
    from pyresttest import binding
    from pyresttest import parsing
    from pyresttest import contenthandling
except ImportError:  # Then try a relative import if possible
    from .. import validators
    from .. import binding
    from .. import parsing
    from .. import contenthandling

class JMESPathExtractor(validators.AbstractExtractor):
    """ Extractor that uses JMESPath syntax
        See http://jmespath.org/specification.html for details
    """
    extractor_type = 'jmespath'
    is_body_extractor = True

    def extract_internal(self, query=None, args=None, body=None, headers=None):
        mybody = body
        if PYTHON_MAJOR_VERSION > 2:
            if isinstance(mybody, bytes):
                mybody = str(mybody, 'utf-8')

        try:
            res = jmespath.search(query, json.loads(mybody)) # Better way
            return res
        except Exception as e:
            raise ValueError("Invalid query: " + query + " : " + str(e))

    @classmethod
    def parse(cls, config):
        base = JMESPathExtractor()
        return cls.configure_base(config, base)
        return base

EXTRACTORS = {'jmespath': JMESPathExtractor.parse}
