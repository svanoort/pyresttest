pyresttest
==========

# What?
- Python utility for testing and benchmarking RESTful services.
- Tests are defined with YAML config files


# License
Apache License, Version 2.0

# Features
* Easily define sets of tests in YAML files.
* Ability to import test sets into other test sets.
* Optional interactive mode for debugging and demonstrations.
* Benchmarking (soon)!

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

    # Not implemented yet, will allow retrying test on failure
    - retries: 7

    # Would allow parallel test execution, not implemented yet
    - test_parallel: False
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
    # Yes, you can do PUT/POST/DELETE when impl is finished
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

There are 3 top level test syntax elements:
- *url:* a simple test, fetches given url via GET request and checks for good response code
- *test*: a fully defined test (see below)
- *config* or *configuration*: overall test configuration
- *import*: (not implemented yet) import test set into another test so you Don't Repeat Yourself


## Syntax Limitations
Whenever possible, I've tried to make reading configuration Be Smart And Do The Right Thing.  That means type conversions are handled wherever possible,
and fail early if configuration is nonsensical.

We're all responsible adults: don't try to give a boolean or list where an integer is expected and it'll play nice.


# Benchmarking?
No, not yet.  When this is done being implemented and tested, benchmarking will be done by a special configuration element underneath the test configuration.

This means by default any defined test call can easily be converted to do microbenchmark too, with the ability to report statistics


# Troubleshoot

## Cannot find argparse, pycurl, or yaml
```
sudo su -
easy_install argparse pyyaml pycurl
exit
```

OR via pip
```
sudo su -
pip install argparse pyyaml pycurl
exit
```

# FAQ

## Why not pure-python tests?
This is intended for use in an environment where Python isn't the primary language.  You only need to know a little YAML to be able to throw together a working test for a REST API written in Java, Ruby, Python, node.js, etc.


## Why YAML and not XML/JSON?
- It's human readable and human editable
- XML is extremely verbose, reducing readability, and tests are supposed to be written by people
- JSON is actually a subset of YAML, so you still can use JSON to define tests, it's just more verbose