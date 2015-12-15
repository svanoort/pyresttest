pyresttest
==========

# Table of Contents

- [What Is It?](#what-is-it)
- [Key Facts](#key-facts)
- [System Requirements](#system-requirements)
- [Sample Test](#sample-test)
- [Examples](#examples)
- [How Do I Get It?](#how-do-i-get-it)
- [How Do I Use It?](#how-do-i-use-it)
	- [Running A Simple Test](#running-a-simple-test)
	- [Using JSON Validation](#using-json-validation)
	- [Interactive Mode](#interactive-mode)
	- [Verbose Output](#verbose-output)
- [Other Goodies](#other-goodies)
- [Basic Test Set Syntax](#basic-test-syntax)
	- [Import example](#import-example)
	- [Url Test](#url-test)
	- [Custom HTTP Options (special curl settings)](#custom-http-options-special-curl-settings)
	- [Syntax Limitations](#syntax-limitations)
- [Benchmarking?](#benchmarking)
	- [Metrics](#metrics)
	- [Benchmark report formats:](#benchmark-report-formats)
- [Installation: Troubleshooting and Special Cases](#installation-troubleshooting-and-special-cases)
- [Project Policies](#project-policies)
- [FAQ](#faq)
- [Feedback and Contributions](#feedback-and-contributions)

# What Is It?
- A REST testing and API microbenchmarking tool
- Tests are defined in basic YAML or JSON config files, no code needed
- Minimal dependencies (pycurl, pyyaml), making it easy to deploy on-server for smoketests/healthchecks
- Supports [generate/extract/validate](advanced_guide.md) mechanisms to create full test scenarios
- Returns exit codes on failure, to slot into automated configuration management/orchestration tools (also supplies parseable logs)
- Logic is written and [extensible](extensions.md) in Python

# Key Facts
Apache License, Version 2.0

![Status Badge](http://52.4.228.82:8080/jenkins/buildStatus/icon?job=set-main-build-status) [![PyPI version](https://badge.fury.io/py/pyresttest.svg)](https://badge.fury.io/py/pyresttest) 
[![PyPI](https://img.shields.io/pypi/dm/Pyresttest.svg)]()

[![Join the chat at https://gitter.im/svanoort/pyresttest](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/svanoort/pyresttest?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[Changelog](CHANGELOG.md) shows the past and present, [milestones](https://github.com/svanoort/pyresttest/milestones) show the future roadmap.

* The changelog will also show features/fixes currently merged to the master branch but not released to pip yet (pending installation tests across platforms). 

# System Requirements
- Linux or Mac OS X with python 2.6/2.7 or 3.3+ (alpha level support) and pycurl working. See [Installation](#how-do-i-get-it)
- Do not use a virtualenv, this is currently unsupported due to issues with libcurl (PRs with tests welcome!)

# Sample Test
**This will check that APIs accept operations, and will smoketest an application**
```yaml
---
- config:
    - testset: "Basic tests"

- test: 
    - name: "Basic get"
    - url: "/api/person/"
- test: 
    - name: "Get single person"
    - url: "/api/person/1/"
- test: 
    - name: "Delete a single person, verify that works"
    - url: "/api/person/1/"
    - method: 'DELETE'
- test: # create entity by PUT
    - name: "Create/update person"
    - url: "/api/person/1/"
    - method: "PUT"
    - body: '{"first_name": "Gaius","id": 1,"last_name": "Baltar","login": "gbaltar"}'
    - headers: {'Content-Type': 'application/json'}
    - validators:  # This is how we do more complex testing!
        - compare: {header: content-type, comparator: contains, expected:'json'}
        - compare: {jsonpath_mini: 'login', expected: 'gbaltar'}  # JSON extraction
        - compare: {raw_body:"", comparator:contains, expected: 'Baltar' }  # Tests on raw response
- test: # create entity by POST
    - name: "Create person"
    - url: "/api/person/"
    - method: "POST"
    - body: '{"first_name": "William","last_name": "Adama","login": "theadmiral"}'
    - headers: {Content-Type: application/json}
  ```
# Examples
* The [Quickstart](quickstart.md) should be *everyone's* starting point
* Here's a [really good example](examples/miniapp-extract-validate.yaml) for how to create a user and then do tests on it.  
  - This shows how to use extraction from responses, templating, and different test types
* If you're trying to do something fancy, take a look at the [content-test.yaml](pyresttest/content-test.yaml).
  - This shows most kinds of templating & variable uses. It shows how to read from file, using a variable in the file path, and templating on its content!
* PyRestTest isn't limited to JSON; there's an [example for submitting form data](https://github.com/svanoort/pyresttest/tree/master/examples/dummyapp-posting-forms.yaml)
* There's a [whole folder](https://github.com/svanoort/pyresttest/tree/master/examples) of example tests to help get started

# How Do I Get It?
The best way to install PyRestTest is via Python's pip packaging tool.

If that is not installed, we'll need to install it first:
* Ubuntu/Debian: (sudo) `apt-get install python-pip`
* CentOS/RHEL: (sudo) `yum install python-pip`
* Mac OS X with homebrew: `brew install python`  (it's included)
* Or with just python installed: `wget https://bootstrap.pypa.io/get-pip.py && sudo python get-pip.py`

**Then install package python-pycurl:**
* Ubuntu: (sudo) `apt-get install python-pycurl`
* CentOS/RHEL: (sudo) `yum install python-pycurl`
*This is needed because the pycurl dependency may fail to install by pip.*

Then we install pyresttest:
```shell
sudo pip install pyresttest
```

**If it fails like this:** 
`__main__.ConfigurationError: Could not run curl-config: [Errno 2] No such file or directory`

Then you need to install python-pycurl (pip tried and failed to install it)

There are also options to [install from repo](#installation-without-pip), or [build an RPM](#pure-rpm-based-install).

# How Do I Use It?
- The [Quickstart](quickstart.md) walks through common use cases
- Benchmarking has its [own section](#benchmarking) below
- Advanced features have [separate documentation](advanced_guide.md) (templating, generators, content extraction, complex validation).
- How to [extend PyRestTest](extensions.md) is its own document
- There are a [ton of examples](https://github.com/svanoort/pyresttest/tree/master/examples)

## Running A Simple Test

Run a basic test of the github API:

```shell
resttest.py https://api.github.com examples/github_api_smoketest.yaml
```

## Using JSON Validation

A simple set of tests that show how json validation can be used to check contents of a response.
Test includes both successful and unsuccessful validation using github API.

```shell
resttest.py https://api.github.com examples/github_api_test.yaml
```

(For help: python resttest.py  --help )

## Interactive Mode
Same as the other test but running in interactive mode.

```python
resttest.py https://api.github.com examples/github_api_test.yaml --interactive true --print-bodies true
```

## Verbose Output

```shell
resttest.py https://api.github.com examples/github_api_test.yaml --log debug
```


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

## Import example
```yaml
---
# Will load the test sets from miniapp-test.yaml and run them
- import: examples/miniapp-test.yaml
```

## Url Test
A simple URL test is equivalent to a basic GET test with that URL
```yaml
---
- config:
    - testset: "Basic tests"
- url: "/api/person/"  # This is a simple test
- test: 
    - url: "/api/person/"  # This does the same thing
```

## Custom HTTP Options (special curl settings)
For advanced cases, sometimes you will want to use custom Curl settings that don't have a corresponding option in PyRestTest.  

This is easy to do: for each test, you can specify custom Curl arguments with 'curl_option_optionname.'  For this, 'optionname' is case-insensitive and the optionname is a [Curl Easy Option](http://curl.haxx.se/libcurl/c/curl_easy_setopt.html) with 'CURLOPT_' removed. 

For example, to follow redirects up to 5 times (CURLOPT_FOLLOWLOCATION and CURLOPT_MAXREDIRS):
```yaml
---
- test: 
    - url: "/api/person/1"
    - curl_option_followlocation: True
    - curl_option_maxredirs: 5  
```
Note that while option names are validated, *no validation* is done on their values.

## Syntax Limitations
Whenever possible, I've tried to make reading configuration Be Smart And Do The Right Thing.  That means type conversions are handled wherever possible,
and fail early if configuration is nonsensical.

We're all responsible adults: don't try to give a boolean or list where an integer is expected and it'll play nice.

One caveat: *if you define the same element (example, URL) twice in the same enclosing element, the last value will be used.*  In order to preserve sanity, I use last-value wins.


# Benchmarking?
Oh, yes please! PyRestTest allows you to collect low-level network performance metrics from Curl itself.

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
- *Aggregates*: runs a reduction function to return a single value over the entire benchmark run (median, average, etc)

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

## Curl ConfigurationError on Pip Install
If you get an error like this on installation:
```__main__.ConfigurationError: Could not run curl-config: [Errno 2] No such file or directory```

Then the PyCurl installation is broken.  This is easily fixed by installing needed libcurl libraries and then trying to install:

- On Ubuntu/Debian: `sudo apt-get install libcurl4-openssl-dev`
- On CentOS/RHEL: `yum install libcurl-devel`

## Installation without Pip
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
sudo yum install PyYAML python-pycurl
```
- You need to install PyYAML & PyCurl manually because Python distutils can't translate python dependencies to RPM packages. 

**Gotcha:** Python distutils add a dependency on your major python version. 
**This means you can't build an RPM for a system with Python 2.6 on a Python 2.7 system.**

## Building an RPM for RHEL 6/CentOS 6
You'll need to install rpm-build, and then it should work.

```shell
sudo yum install rpm-build
```

# Project Policies
* PyRestTest uses the Github flow
  - The master branch is an integration branch for mature features
  - Releases are cut periodically from master (every 3-6 months generally, or more often if breaking bugs are present) and released to PyPi
  - Feature development is done in feature branches and merged to master by PR when tested (validated by continuous integration in Jenkins)
  - The 'stable' branch tracks the last release, use this if you want to run PyRestTest from source
* [The changelog is here](CHANGELOG.md), this will show past releases and features merged to master for the next release but not released 
* Python 2.6 and 2.7 compatible (tested on Ubuntu 14/python 2.7 and CentOS 6/python 6.6)
* [Working on Python 3 support](https://github.com/svanoort/pyresttest/issues/98)
* Releases occur every few months to [PyPi](https://pypi.python.org/pypi/pyresttest/) once a few features are ready to go
* PyRestTest uses [Semantic Versioning 2.0](http://semver.org/)
* **Back-compatibility is important! PyRestTest makes a strong effort to maintain command-line and YAML format back-compatibility since 1.0.**
  - [Extension method signatures](extensions.md) are maintained as much as possible. 
  - However, internal python implementations are subject to change.
  - Major version releases (1.x to 2.x, etc) may introduce breaking API changes, but only *with a really darned good reason, and only there's not another way.*

# FAQ

## Why not pure-python tests?
- This is written for an environment where Python is not the sole or primary langauge
- **You totally can do pure-Python tests if you want!**  
    - [Extensions](extensions.md) provide a stable API for adding more complex functionality in python
    - All modules can be imported and used as libraries
    - Gotcha: the project is still young, so internal implementation may change often, much more than YAML features

## Why YAML and not XML/JSON?
- XML is extremely verbose and has many gotchas for parsing
- You **CAN use JSON for tests**, it's a subset of YAML. See [miniapp-test.json](examples/miniapp-test.json) for an example. 
- YAML tends to be the most concise, natural, and easy to write of these three options

## Does it do load tests?
- No, this is a separate niche and there are already many excellent tools to fill it
- Adding load testing features would greatly increase complexity
- But some form might come eventually!

# Feedback and Contributions
We welcome any feedback you have, including pull requests, reported issues, etc!
**For new contributors** there are a whole set of issues labelled with [help wanted](https://github.com/svanoort/pyresttest/labels/help%20wanted) which are excellent starting points to offer a contribution! 

For instructions on how to set up a dev environment for PyRestTest, see [building.md](building.md).

For pull requests to get easily merged, please:
- Include unit tests (and functional tests, as appropriate) and verify that run_tests.sh passes
- Include documentation as appropriate
- Attempt to adhere to PEP8 style guidelines and project style

Bear in mind that this is largely a one-man, outside-of-working-hours effort at the moment, so response times will vary.  That said: every feature request gets heard, and even if it takes a while, all the reasonable features will get incorporated.  **If you fork the main repo, check back periodically... you may discover that the next release includes something to meet your needs and then some!**
