import resttest
import unittest
import json
import yaml

class TestRestTest(unittest.TestCase):
    """ Tests to test a REST testing framework, how meta is that? """

    def setUp(self):
        pass

    def test_build_test(self):
        """ Test basic ways of creating test objects from input object structure """

        #Most basic case
        input = {"url": "/ping", "method": "DELETE", "NAME":"foo", "group":"bar", "body":"<xml>input</xml>","headers":{"Accept":"Application/json"}}
        test = resttest.build_test('',input)
        self.assertTrue(test.url == input['url'])
        self.assertTrue(test.method == input['method'])
        self.assertTrue(test.name == input['NAME'])
        self.assertTrue(test.group == input['group'])
        self.assertTrue(test.body == input['body'])
        #Test headers match
        self.assertFalse( set(test.headers.values()) ^ set(input['headers'].values()) )

        #Happy path, only gotcha is that it's a POST, so must accept 200 or 204 response code
        input = {"url": "/ping", "meThod": "POST"}
        test = resttest.build_test('',input)
        self.assertTrue(test.url == input['url'])
        self.assertTrue(test.method == input['meThod'])
        self.assertTrue(test.expected_status == [200,201,204])

        #Test that headers propagate
        input = {"url": "/ping", "method": "GET", "headers" : [{"Accept":"application/json"},{"Accept-Encoding":"gzip"}] }
        test = resttest.build_test('',input)
        expected_headers = {"Accept":"application/json","Accept-Encoding":"gzip"}

        self.assertTrue(test.url == input['url'])
        self.assertTrue(test.method == 'GET')
        self.assertTrue(test.expected_status == [200])
        self.assertTrue(isinstance(test.headers,dict))

        #Test no header mappings differ
        self.assertFalse( set(test.headers.values()) ^ set(expected_headers.values()) )


        #Test expected status propagates and handles conversion to integer
        input = [{"url": "/ping"},{"name": "cheese"},{"expected_status":["200",204,"202"]}]
        test = resttest.build_test('',input)
        self.assertTrue(test.name == "cheese")
        print test.expected_status
        self.assertTrue(test.expected_status == [200,204,202])

    def test_safe_boolean(self):
        """ Test safe conversion to boolean """
        self.assertFalse(resttest.safe_to_bool(False))
        self.assertTrue(resttest.safe_to_bool(True))
        self.assertTrue(resttest.safe_to_bool('True'))
        self.assertTrue(resttest.safe_to_bool('true'))
        self.assertTrue(resttest.safe_to_bool('truE'))
        self.assertFalse(resttest.safe_to_bool('false'))

        #Try things that should throw exceptions
        try:
            boolean = resttest.safe_to_bool('fail')
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass #Good

        try:
            boolean = resttest.safe_to_bool([])
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass #Good

        try:
            boolean = resttest.safe_to_bool(None)
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass #Good


    def test_make_configuration(self):
        input = {"url": "/ping", "method": "DELETE", "NAME":"foo", "group":"bar", "body":"<xml>input</xml>","headers":{"Accept":"Application/json"}}
        test = resttest.make_configuration(input)
        self.assertTrue


        input = {"url": "/ping", "method": "DELETE", "NAME":"foo", "group":"bar", "body":"<xml>input</xml>","headers":{"Accept":"Application/json"}}

        pass

    def test_flatten(self):
        """ Test flattening of lists of dictionaries to single dictionaries """

        #Test happy path: list of single-item dictionaries in
        array = [{"url" : "/cheese"}, {"method" : "POST"}]
        expected = {"url" :"/cheese", "method" : "POST"}
        output = resttest.flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual

        #Test dictionary input
        array = {"url" : "/cheese", "method" : "POST"}
        expected = {"url" : "/cheese", "method" : "POST"}
        output = resttest.flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertTrue( len(set(output.items()) ^ set(expected.items())) == 0) #Test that expected output matches actual

        #Test empty list input
        array = []
        expected = {}
        output = resttest.flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual

        #Test empty dictionary input
        array = {}
        expected = {}
        output = resttest.flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual

        #Test mixed-size input dictionaries
        array = [{"url" : "/cheese"}, {"method" : "POST", "foo" : "bar"}]
        expected = {"url" : "/cheese", "method" : "POST", "foo" : "bar"}
        output = resttest.flatten_dictionaries(array)
        self.assertTrue(isinstance(output,dict))
        self.assertFalse( len(set(output.items()) ^ set(expected.items())) ) #Test that expected output matches actual


if __name__ == '__main__':
    unittest.main()