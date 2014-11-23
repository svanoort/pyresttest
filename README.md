pyresttest
==========

# What Is It?
- A simple but powerful REST testing and benchmarking framework
- Minimal dependencies, designed to slot into automated configuration management/orchestration tools
- Tests are defined in basic YAML or JSON config files, no code needed
- Logic is written and extensible in Python

# License
Apache License, Version 2.0

# How Do I Get It?
The best way to install PyRestTest is via Python's pip packaging tool.

If that is not installed, we'll need to install it first:
```shell
wget https://bootstrap.pypa.io/get-pip.py && sudo python get-pip.py
```
Then we install pyresttest:
```shell
sudo pip install pyresttest
```

There are also options to [install from repo](#installation-without-pip), or [build an RPM](#pure-rpm-based-install).

# How Do I Use It?
The [Quickstart](#getting-started-quickstart-requirements) is below. 

There's an explanation for how to use it with [benchmarking below](#benchmarking).

There is [separate documentation](advanced_guide.md) for the more advanced features (templating, generators, content extraction, complex validation).

The root folder of this library also includes a ton of example tests.

## Running A Simple Test

Run a simple test that checks a URL returns a 200:

```shell
resttest.py https://github.com simple_test.yaml
```

## Using JSON Validation

A simple set of tests that show how json validation can be used to check contents of a response.
Test includes both successful and unsuccessful validation using github API.

```shell
resttest.py https://api.github.com github_api_test.yaml
```

(For help: python resttest.py  --help )

## Interactive Mode
Same as the other test but running in interactive mode.

```python
resttest.py https://api.github.com github_api_test.yaml --interactive true --print-bodies true
```

## Verbose Output

```shell
resttest.py https://api.github.com github_api_test.yaml --log debug
```

# Getting Started: Quickstart Requirements
Now, let's get started!  

**Most quickstarts show a case where *everything works perfectly.***

**That is *not* what we're going to do today.** 

**We're going to break things horribly and enjoy it!**

**This is what testing is for.**

## System Requirements:
- A semi-modern linux distro (or maybe Mac OS X)
- Do not use a virtualenv (or have it custom configured to find libcurl)

# Quickstart Part 0: Setting Up a Sample REST Service
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

# Quickstart Part 1: Our First (Smoke) Test
In our second terminal, we're going to create a basic REST smoketest, which can be used to test the server came up cleanly and works.

Pop up ye olde text editor of choice and save this to a file named 'test.yaml':

```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - name: "Basic smoketest"
    - url: "/api/people/"
```

And when we run it:
```shell
resttest.py http://localhost:8000 test.yaml
```

**OOPS!**  As the more observant people will notice, **we got the API URL wrong**, and the test failed, showing the unexpected 404, and reporting the test name.  At the end we see the summary, by test group ("Default" is exactly like what it sounds like).  

**Let's fix that, add a test group name, and re-run it!**
```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - group: "Quickstart"
    - name: "Basic smoketest"
    - url: "/api/person/"
```

Ahh, *much* better!  But, that's very basic, surely we can do *better?*


# Quickstart Part 2: Functional Testing - Create/Update/Delete
Let's build this out into a full test scenario, creating and deleting a user:

We're going to add a create for a new user, that scoundrel Gaius Baltar:
```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - group: "Quickstart"
    - name: "Basic smoketest"
    - url: "/api/person/"

- test:
    - group: "Quickstart"
    - name: "Create a person"
    - url: "/api/person/10/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 10,"last_name": "Baltar","login": "baltarg"}'
```
... and when we run it, it fails (500 error).  That sneaky lowdown tried to sneak in without a Content-Type so the server knows what he is. 

**Let's fix it...**

```yaml
- test:
    - group: "Quickstart"
    - name: "Create a person"
    - url: "/api/person/10/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 10,"last_name": "Baltar","login": "baltarg"}'
    - headers: {'Content-Type': 'application/json'}
```

... and now both tests will pass. 
Then let's add a test the person is really there after:

```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - group: "Quickstart"
    - name: "Basic smoketest"
    - url: "/api/person/"

- test:
    - group: "Quickstart"
    - name: "Create a person"
    - url: "/api/person/10/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 10,"last_name": "Baltar","login": "baltarg"}'
    - headers: {'Content-Type': 'application/json'}

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar was added"
    - url: "/api/person/10/"
```

**Except there is a problem with this... the third test will pass if Baltar already existed in the database.  Let's test he wasn't there beforehand...**

```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar ISN'T there to begin with"
    - url: "/api/person/10/"
    - expected_status: [404]

- test:
    - group: "Quickstart"
    - name: "Basic smoketest"
    - url: "/api/person/"

- test:
    - group: "Quickstart"
    - name: "Create a person"
    - url: "/api/person/10/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 10,"last_name": "Baltar","login": "baltarg"}'
    - headers: {'Content-Type': 'application/json'}

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar is there after we added him"
    - url: "/api/person/10/"
```

**Much better, now the first test fails... so, let's add a delete for that user at the end of the test, and check he's really gone.**

```yaml
---
- config:
    - testset: "Quickstart app tests"

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar ISN'T there to begin with"
    - url: "/api/person/10/"
    - expected_status: [404]

- test:
    - group: "Quickstart"
    - name: "Basic smoketest"
    - url: "/api/person/"

- test:
    - group: "Quickstart"
    - name: "Create a person"
    - url: "/api/person/10/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 10,"last_name": "Baltar","login": "baltarg"}'
    - headers: {'Content-Type': 'application/json'}

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar is there after we added him"
    - url: "/api/person/10/"

- test:
    - group: "Quickstart"
    - name: "Get rid of Gaius Baltar!"
    - url: "/api/person/10/"
    - method: 'DELETE'

- test:
    - group: "Quickstart"
    - name: "Make sure Mr Baltar ISN'T there after we deleted him"
    - url: "/api/person/10/"
    - expected_status: [404]
```

**And now we have a full lifecycle test of creating, fetching, and deleting a user via the API.**

**This is just a starting point,** see the [advanced guide](advanced_guide.md) for the advanced features (templating, generators, content extraction, complex validation).

# Other Goodies
* Simple templating of HTTP request bodies, URLs, and validators, with user variables
* Generators to create dummy data for testing, with support for easily writing your own
* Sequential tests: extract info from one test to use in the next
* Import test sets in other test sets, to compose suites of tests easily
* Easy benchmarking: convert any test to a benchmark, by changing the element type and setting output options if needed
* Lightweight benchmarking: ~0.3 ms of overhead per request, and plans to reduce that in the future
* Accurate benchmarking: network measurements come from native code in LibCurl, so test overhead doesn't alter them
* Optional interactive mode for debugging and demos

# Basic Test Set Syntax
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
It's easy to build and install from RPM:

## Building the RPM:
```shell
python setup.py bdist_rpm  # Build RPM
find -iname '*.rpm'   # Gets the RPM name
```
### Installing from RPM
```shell
sudo yum localinstall my_rpm_name
sudo yum install PyYAML
```
- You need to install PyYAML manually because Python distutils can't translate python dependencies to RPM packages. 
- This is not needed for PyCurl because it is built in by default

**Gotcha:** Python distutils add a dependency on your major python version. 
**This means you can't build an RPM for a system with Python 2.6 on a Python 2.7 system.**

## Building an RPM for RHEL 6/CentOS 6
You'll need to install rpm-build, and then it should work.

```shell
sudo yum install rpm-build
```

# FAQ

## Why not pure-python tests?
- This is written for an environment where Python is not the sole or primary langauge
- **You totally can do pure-Python tests if you want!**  
    - Gotcha: I will break back compatibility of the implementation often and badly, at least at first
    - Read before you assume: template handling is more complex than you think.
    - Framework run/execute methods in pyresttest/resttest.py do *quite* a bit of heavy lifting

## Why YAML and not XML/JSON?
- XML is extremely verbose and has many gotchas for parsing
- You **CAN use JSON for tests**, it's a subset of YAML. See [miniapp-test.json](miniapp-test.json) for an example. 
- YAML tends to be the most concise, natural, and easy to write of these three options

# Future Plans (rough priority order)
Top priority, before enhancements: 
- bugfixes
- high-value minor usability enhancements (defaults, better error case handling)

0. Refactor complex runner/executor methods into extensible, composable structures for a testing lifecycle
1. Support for cert-based authentication (simply add test config elements and parsing)
2. Smarter reporting, better reporting/logging of test execution and failures
3. Depends on 0: support parallel execution of a test set where extract/generators not used
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
