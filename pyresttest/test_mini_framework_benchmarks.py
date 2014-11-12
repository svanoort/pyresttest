# Benchmarks parts of program to seee what testing overhead is like

import timeit

# Test basic pycurl create/delete, time is ~2.5 microseconds
time = timeit.timeit("mycurl=Curl(); mycurl.close()", setup="from pycurl import Curl", number=1000000)
print 'Curl create/destroy runtime for 1M runs (s)'+str(time)

# Test test interpret/build & configuration speeds for resttest
# Runtime is 36.29 sec, so 36 microseconds per run, or 0.036 ms
time = timeit.timeit("mytest=Test.build_test('', input); mycurl=mytest.configure_curl(); mycurl.close()",
        setup='from resttest import Test; input = {"url": "/ping", "method": "DELETE", "NAME":"foo", "group":"bar", "body":"<xml>input</xml>","headers":{"Accept":"Application/json"}}',
        number=1000000)
print 'Test interpret/configure test config for 1M runs (s)'+str(time)

# Just configuring the curl object from a pre-built test
# 10s/1M runs, or 0.01 ms per
time = timeit.timeit("mycurl=mytest.configure_curl(); mycurl.close()",
        setup='from resttest import Test; input = {"url": "/ping", "method": "DELETE", "NAME":"foo", "group":"bar", "body":"<xml>input</xml>","headers":{"Accept":"Application/json"}}; mytest=Test.build_test("", input);',
        number=1000000)
print 'Test configure curl for 1M runs (s)'+str(time)

# Time for full curl execution on Django testing rest app
# Time: 41.4s for 10k runs, or about 4.14 ms per
timeit.timeit("mycurl=mytest.configure_curl(); mycurl.setopt(pycurl.WRITEFUNCTION, lambda x: None); mycurl.perform(); mycurl.close()",
        setup='import pycurl; from resttest import Test; input = {"url": "/api/person/", "NAME":"foo", "group":"bar"}; mytest=Test.build_test("http://localhost:8000", input);',
        number=10000)

# Github perf test, 27 s for 100 runs = 270 ms per
timeit.timeit("mycurl=mytest.configure_curl(); mycurl.setopt(pycurl.WRITEFUNCTION, lambda x: None); mycurl.perform(); mycurl.close()",
    setup='import pycurl; from resttest import Test; input = {"url": "/search/users?q=jewzaam", "NAME":"foo", "group":"bar"}; mytest=Test.build_test("https://api.github.com", input);',
    number=100)

