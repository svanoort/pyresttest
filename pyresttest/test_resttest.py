import json
import math
import string
import yaml
import unittest

from . import resttest
from .resttest import *


class TestRestTest(unittest.TestCase):
    """ Tests to test overall REST testing framework, how meta is that? """

    def test_jmespath_import(self):
        """ Verify that JMESPath extractor loads if class present """

        importable = False
        try:
            import jmespath
            importable = True            
        except ImportError:
            print("Skipping jmespath import test because library absent")
            raise unittest.SkipTest("JMESPath module absent")

        from . import validators
        self.assertTrue('jmespath' in validators.EXTRACTORS)
        jmespathext = validators.EXTRACTORS['jmespath']('test1.a')

if __name__ == '__main__':
    unittest.main()
