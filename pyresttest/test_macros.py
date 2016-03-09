import unittest

from . import macros
from .macros import *

class TestMacros(unittest.TestCase):
    def test_parse_headers(self):
        """ Basic header parsing tests """
        headerstring = u'HTTP/1.1 200 OK\r\nDate: Mon, 29 Dec 2014 02:42:33 GMT\r\nExpires: -1\r\nCache-Control: private, max-age=0\r\nContent-Type: text/html; charset=ISO-8859-1\r\nX-XSS-Protection: 1; mode=block\r\nX-Frame-Options: SAMEORIGIN\r\nAlternate-Protocol: 80:quic,p=0.02\r\nTransfer-Encoding: chunked\r\n\r\n'
        header_list = parse_headers(headerstring)
        header_dict = dict(header_list)

        self.assertTrue(isinstance(header_list, list))
        self.assertEqual('-1', header_dict['expires'])
        self.assertEqual('private, max-age=0', header_dict['cache-control'])
        self.assertEqual(8, len(header_dict))

        # Error cases
        # No headers
        result = parse_headers("")  # Shouldn't throw exception
        self.assertTrue(isinstance(result, list))
        self.assertEqual(0, len(result))

        # Just the HTTP prefix
        result = parse_headers(
            'HTTP/1.1 200 OK\r\n\r\n')  # Shouldn't throw exception
        self.assertTrue(isinstance(result, list))
        self.assertEqual(0, len(result))

    def test_parse_headers_multiples(self):
        """ Test headers where there are duplicate values set """
        headerstring = u'HTTP/1.1 200 OK\r\nDate: Mon, 29 Dec 2014 02:42:33 GMT\r\nAccept: text/html\r\nAccept: application/json\r\n\r\n'
        headers = parse_headers(headerstring)

        self.assertTrue(isinstance(headers, list))
        self.assertEqual(3, len(headers))
        self.assertEqual(('date', 'Mon, 29 Dec 2014 02:42:33 GMT'), headers[0])
        self.assertEqual(('accept', 'text/html'), headers[1])
        self.assertEqual(('accept', 'application/json'), headers[2])
