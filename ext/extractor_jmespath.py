import json

import jmespath

from py3resttest import validators


class JMESPathExtractor(validators.AbstractExtractor):
    """ Extractor that uses JMESPath syntax
        See http://jmespath.org/specification.html for details
    """
    extractor_type = 'jmespath'
    is_body_extractor = True

    def extract_internal(self, query=None, args=None, body=None, headers=None):
        if isinstance(body, bytes):
            body = str(body, 'utf-8')

        try:
            res = jmespath.search(query, json.loads(body))
            return res
        except Exception as e:
            raise ValueError("Invalid query: " + query + " : " + str(e))

    @classmethod
    def parse(cls, config):
        base = JMESPathExtractor()
        return cls.configure_base(config, base)


EXTRACTORS = {'jmespath': JMESPathExtractor.parse}
