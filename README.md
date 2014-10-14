pyresttest
==========

# What?
- Python utility for testing and benchmarking RESTful services.
- Tests are defined with YAML or JSON config files


# License
Apache License, Version 2.0

# Features
* Easily define sets of tests in YAML or JSON files
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
- *output_file*: file name to write benchmark output to (MUST be defined), will get overwritten with each run
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
    - ouput_format: json
    - output_file: 'miniapp-single.json'
```

# Troubleshooting

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

That said, there's nothing stopping you from doing the tests in python.


## Why YAML and not XML/JSON?
- It's human readable and human editable
- XML is extremely verbose, reducing readability, and tests are supposed to be written by people
- JSON is actually a subset of YAML, so you still can use JSON to define tests, it's just more verbose. See miniapp-test.json for an example.  Just remember that you have to escape quotes when giving JSON input to request bodies.