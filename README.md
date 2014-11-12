pyresttest
==========

# What?
- A simple but powerful REST testing and benchmarking framework
- Tests are defined in basic YAML or JSON config files, no code needed
- Logic is written and extensible in Python
- Minimal dependencies

# License
Apache License, Version 2.0

# Installation
The best way to install PyRestTest is via Python's pip packaging tool.

If that is not installed, we'll need to install it first:
```shell
wget https://bootstrap.pypa.io/get-pip.py && sudo python get-pip.py
```
Then we install pyresttest:
```shell
sudo pip install pyresttest
```

There are also options to install from repo, or build an RPM for your use (see at bottom).

Now, let's get started!  The following should work on most modern linux distros and perhaps on Mac OS X. 


# Advanced Features/Syntax Guide
There is [separate documentation](advanced_guide.md) for the advanced features (templating, generators, content extraction, complex validation).


# Quickstart Part 1: Setting Up a Sample REST Service
In order to get started with PyRestTest, we will need a REST service with an API to work with.

Fortunately, there is a small RESTful service included with the project. 

Let's **grab a copy of the code** to start:
```shell
git clone https://github.com/svanoort/pyresttest.git
```

Then we'll **install the necessary dependencies** to run it (Django and Django Tastypie):
```shell
sudo pip install 'django >=1.6, <1.7' django-tastypie
```
Now **we start a test server in one terminal** (on default port 8000) with some preloaded data, and we will test in a second terminal:
```shell
cd pyresttest/pyresttest/testapp
python manage.py testserver test_data.json
```

**If you get an error like this**, it's because you're using Python 2.6, and are trying to run a Django version not compatible with that:
```
Traceback (most recent call last):
  File "/usr/bin/django-admin.py", line 2, in <module>
    from django.core import management
  File "/usr/lib64/python2.6/site-packages/django/core/management/__init__.py", line 68
    commands = {name: 'django.core' for name in find_commands(__path__[0])}
```

This is easy enough to fix though by installing a compatible Django version:
```shell
sudo pip uninstall -y django django-tastypie
sudo pip install 'django >=1.6, <1.7' django-tastypie
```
**Before going deeper, let's make sure that server works okay... in our second terminal, we run this:**
```shell
curl -s http://localhost:8000/api/person/2/ | python -m json.tool
```

**If all is good, we ought to see a result like this:**
```json
{
    "first_name": "Leeroy", 
    "id": 2, 
    "last_name": "Jenkins", 
    "login": "jenkins", 
    "resource_uri": "/api/person/2/"
}
```

**Now, we've got a small but working REST API for PyRestTest to test on!**

# Quickstart Part Two: Starting with testing
TODO: Let's do some basic tests!


# Key Features (not an exhaustive list)
* Full functional testing of REST APIs
* Full support for GET/PUT/POST/DELETE HTTP methods, and custom headers
* Simple templating of HTTP request bodies, URLs, and validators, with user variables
* Read HTTP request bodies from files or inline them
* Generators to create dummy data for testing, with support for easily writing your own
* Simple validation: ensure host is reachable and check HTTP response codes
* Complex validation: check for values in HTTP responses, and do comparisons on them
* Setup/Teardown: extract information from one test to use in the next ones
* Import test sets in other test sets, to compose suites of tests easily
* Easy benchmarking: convert any test to a benchmark, by changing the element type and setting output options if needed
* Lightweight benchmarking: ~0.3 ms of overhead per request, and plans to reduce that in the future
* Accurate benchmarking: network measurements come from native code in LibCurl, so test overhead doesn't alter them
* Optional interactive mode for debugging and demos



After this, you can execute the tests by:
```
resttest.py {host:port/endpoint} {testfile.yaml}
```

# Examples

## Simple Test

Run a simple test that checks a URL returns a 200:

```
python resttest.py https://github.com simple_test.yaml
```

## REST API with JSON Validation

A simple set of tests that show how json validation can be used to check contents of a response.
Test includes both successful and unsuccessful validation using github API.

```
python resttest.py https://api.github.com github_api_test.yaml
```

(For help: python resttest.py  --help )

## Interactive Mode
Same as the other test but running in interactive mode.

```
python resttest.py https://api.github.com github_api_test.yaml --interactive true --print-bodies true
```

## Verbose Output

```
python resttest.py https://api.github.com github_api_test.yaml --log debug
```

# Test Configuration

## Sample Test Syntax

```
---
- config:
    # Name test sets
    - testset: "Sample Tests"

    # Print full response bodies
    - print_bodies: 'False'

- url: "/ping"  # Basic test, just a simple GET
- test: {url: "/ping", method: "GET"}  # Specify method, in-line version
- test: # Defined test
    - url: "/complex"
      group: "Complex"  # Named test group, tests pass/fail is reported by group
      name: "Test complex object"
      method: "GET"
      expected_status: 200  # Expected HTTP Status Codes
- test:
    - url: "/object"
    - method: "GET"
    - headers: # HTTP headers for test
        - Accept: application/json
        - Content-Encoding: lzf
- test:
    - url: "/cheese"
    # Yes, you can do PUT/POST/DELETE, and by default they'll look for 200/204 and 201/202 status codes
    - method: "DELETE"
    - headers: {Content-Type: application/xml, "Content-Encoding": "gzip"}
- test:
    - url: "/complex/100"
    - method: "POST"
    - body: "<xmlhere><tag>contents</tag></xmlhere>"  # Body for the POST method

- import: "more_tests.yaml"  # Import another test file into this one
```


## Basic Test Set Syntax
As you can see, tests are defined in [YAML](http://en.wikipedia.org/wiki/YAML) format.

There are 5 top level test syntax elements:
- *url:* a simple test, fetches given url via GET request and checks for good response code
- *test*: a fully defined test (see below)
- *benchmark*: a fully defined benchmark (see below)
- *config* or *configuration*: overall test configuration
- *import*: import another test set file so you Don't Repeat Yourself


## Syntax Limitations
Whenever possible, I've tried to make reading configuration Be Smart And Do The Right Thing.  That means type conversions are handled wherever possible,
and fail early if configuration is nonsensical.

We're all responsible adults: don't try to give a boolean or list where an integer is expected and it'll play nice.

One caveat: *if you define the same element (example, URL) twice in the same enclosing element, the last value will be used.*  In order to preserve sanity, I use last-value wins.


# Benchmarking?
Oh, yes please! PyRestTest is now benchmark-enabled, allowing you to collect low-level network performance metrics from Curl itself.

Benchmarks are based off of tests: they extend the configuration elements in a test, allowing you to configure the REST call similarly.
However, they do not perform validation on the HTTP response, instead they collect metrics.

There are a few custom configuration options specific to benchmarks:
- *warmup_runs*: (default 10 if unspecified) run the benchmark calls this many times before starting to collect data, to allow for JVM warmup, caching, etc
- *benchmark_runs*: (default 100 if unspecified) run the benchmark this many times to collect data
- *output_file*: (default is None) file name to write benchmark output to, will get overwritten with each run, if none given, will write to terminal only
- *output_format*: (default CSV if unspecified) format to write the results in ('json' or 'csv'). More on this below.
- *metrics*: which metrics to gather (explained below), MUST be specified or benchmark will do nothing


## Metrics
There are two ways to collect performance metrics: raw data, and aggregated stats.
Each metric may yield raw data, plus one or more aggregate values.
- *Raw Data*: returns an array of values, one for each benchmark run
- *Aggregates*: runs a reduction function to return a single value over the entire benchmark run

To return raw data, in the 'metrics' configuration element, simply input the metric name in a list of values.
The example below will return raw data for total time and size of download (101 values each).

```
- benchmark: # create entity
    - name: "Basic get"
    - url: "/api/person/"
    - warmup_runs: 7
    - 'benchmark_runs': '101'
    - output_file: 'miniapp-benchmark.csv'
    - metrics:
        - total_time
        - size_download
```

Aggregates are pretty straightforward:
- *mean* or *mean_arithmetic*: arithmetic mean of data (normal 'average')
- *mean_harmonic*: harmonic mean of data (useful for rates)
- *median*: median, the value in the middle of sorted result set
- *std_deviation*: standard deviation of values, useful for measuring how consistent they are
- *total* or *sum*: total up the values given

Currently supported metrics are listed below, and these are a subset of Curl get_info variables.
These variables are explained here (with the CURLINFO_ prefix removed): [curl_easy_get_info documentation](http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html)

*Metrics:*
'appconnect_time', 'connect_time', 'namelookup_time', 'num_connects', 'pretransfer_time', 'redirect_count', 'redirect_time', 'request_size', 'size_download', 'size_upload', 'speed_download', 'speed_upload', 'starttransfer_time', 'total_time'


## Benchmark report formats:
CSV is the default report format.  CSV ouput will include:
- Benchmark name
- Benchmark group
- Benchmark failure count (raw HTTP failures)
- Raw data arrays, as a table, with headers being the metric name, sorted alphabetically
- Aggregates: a table of results in the format of (metricname, aggregate_name, result)

In JSON, the data is structured slightly differently:
```
{"failures": 0,
"aggregates":
    [["metric_name", "aggregate", "aggregateValue"] ...],
"failures": failureCount,
"group": "Default",
"results": {"total_time": [value1, value2, etc], "metric2":[value1, value2, etc], ... }
}
```

Samples:
```
---
- config:
    - testset: "Benchmark tests using test app"

- benchmark: # create entity
    - name: "Basic get"
    - url: "/api/person/"
    - warmup_runs: 7
    - 'benchmark_runs': '101'
    - output_file: 'miniapp-benchmark.csv'
    - metrics:
        - total_time
        - total_time: mean
        - total_time: median
        - size_download
        - speed_download: median

- benchmark: # create entity
    - name: "Get single person"
    - url: "/api/person/1/"
    - metrics: {speed_upload: median, speed_download: median, redirect_time: mean}
    - output_format: json
    - output_file: 'miniapp-single.json'
```

# Installation: Troubleshooting and Special Cases

# Installation without Pip
```
git clone https://github.com/svanoort/pyresttest.git
cd pyresttest
sudo python setup.py install
```

## Cannot find pycurl, or yaml
```
sudo su -
easy_install pyyaml pycurl
exit
```

OR via pip
```
sudo su -
pip install pyyaml pycurl
exit
```

## Pure RPM-based install?
It's not too complex to build and install from RPM, as long as you're building for systems with the same or higher minor version of Python.

If you try to build on a {on a different version than built, there will be a dependency issue on RPM installation.

See below for special cases with RHEL/CentOS 6.

### Building a basic RPM
```
python setup.py bdist_rpm  # Build RPM
find -iname '*.rpm'   # Gets the RPM name
```

### Installing from RPM
```
sudo yum localinstall my_rpm_name
sudo yum install PyYAML
```
Note that the latter is necessary because Python can't translate python dependencies to RPM packages. 
I am looking to fix this in the future, but it requires quite a bit of additional work.
PyCurl is built in by default to both yum and apt-get, so generally you don't have to install it.


## Building an RPM for RHEL 6/CentOS 6
There are a couple special challenges building RPMs from Python for these operating systems. 
- rpm-build is not installed by default, just RPM, and Python set up tools do not like this
- These operating systems come with Python 2.6.x, not 2.7.  
- If you build the RPM on a Python 2.7 system, that will be a dependency for the RPM

For these operating systems, install RPM build, then build as above **from a system on the same OS version**:
```
sudo yum install rpm-build
```


# FAQ

## Why not pure-python tests?
This is intended for use in an environment where Python isn't the primary language.  You only need to know a little YAML to be able to throw together a working test for a REST API written in Java, Ruby, Python, node.js, etc.

If you want to write tests in pure python, there's nothing stopping this, but a couple notes:
- I've *tried* to separate config parsing and application logic, and test separately. 
- Code is generally separated by concern and commented.  
- Read before you assume, there are implementation details around templating, for example, which can be more complex than anticipated.
- The framework run/execute methods in pyresttest/resttest.py do *quite* a bit of heavy lifting for now.
- Internal implementation is far more subject to change than the YAML syntax


## Why YAML and not XML/JSON?
- It's concise, flexible and legitimately human readable and human editable, even more than JSON
- XML is extremely verbose and has gotchas, reducing readability, and tests are supposed to be written by people
- JSON is a subset of YAML, so you still can use JSON to define tests, it's just more verbose. See miniapp-test.json for an example.  Just remember that you have to escape quotes when giving JSON input to request bodies.
- I feel the readability/writeability gains for YAML outweigh the costs of an extra dependency


## Where does this come from?
Pain and suffering. :)  

No, seriously, this is an answer to a whole series of challenges encountered working with REST APIs.
It started with a simple BASH script used to smoketest services after deployments and maintenance.
Then, it just grew from there. 


# Future Plans (rough priority order)
0. Refactor complex runner/executor methods into extensible, composable structures for a testing lifecycle
1. Support for cert-based authentication (simply add test config elements and parsing)
2. Smarter reporting, better reporting/logging of test execution and failures
3. Depends 0: support parallel execution of a test set where extract/generators not used
4. Repeat tests (for fuzzing) and setUp/tearDown
5. Hooks for reporting on test results
6. Improve Python APIs and document how to do pure-python testing with this
7. Tentative: add a one-pass optimizer for benchmark/test execution (remove redundant templating)

## Feedback
We welcome any feedback you have, including pull requests, reported issues, etc

For pull requests to get easily merged, please:
- Include unit tests
- Include documentation as appropriate
- Attempt to adhere to PEP8 style guidelines and project style

Bear in mind that this is largely a one-man, outside-of-working-hours effort at the moment, so response times will vary.
