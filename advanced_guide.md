Advanced Guide For PyRestTest:
==========

This provides a more detailed guide to using the advanced features of PyRestTest.
Specifically **generators**, **variable binding,** **data extraction,** and **content validators.**

# Templating and Context Basics
- Tests and benchmarks may use variables to template out configuration dynamically.
- Templating is performed using basic [Python string templating](https://docs.python.org/2/library/string.html#template-strings).  
- Templating uses variables contained in a context, and are templates evaluated anew for each test run or benchmark iteration
- Contexts are either passed into a test, or created in the text if not supplied
- Contexts are persistent within a TestSet. Once a variable is set, it can be used in all following tests
- **Context variables are modified and set** in 3 ways:
    1. **Variable values may be statically declared** with 'variable_binds' in TestSet config or the test
    2. **Generator output may be bound to a variable** with 'generator binds' in the test
        + Generators **must be declared by name** in the TestSet config for them to be used
        + Generator bindings evaluate once per HTTP call:
            - **Only once per Test**, and **multiple times for a Benchmark**
        + Generator bindings only apply to the Test/Benchmark they are declared in. New values are generated only when the binding is evaluated.
    3. **Data may be extracted from the HTTP response body** with the 'extract_binds' element in a test. 
        + Note that if the request fails, the data cannot be set (nothing to work with)
        + Currently, this is unsupported for benchmarks: using extraction doesn't make sense because benchmarks should be isolated.

## Templating, Generators, and Binding Example
What if you want to benchmark creating/updating a series of users, but the users must have unique IDs and logins?

*Easy-peasy with generators!*  You simply declare a number sequence generator, and bind it to the ID field for a PUT benchmark. 

To demonstrate static variable binding, this does binding for both first and last names too.

**Example:**
```yaml
---
- config:
    - testset: "Benchmark tests using test app"
    # Variables to use in the test set
    - variable_binds: {firstname: 'Gaius-Test', lastname: 'Baltar-Test'}
    # Generators to use in the test set
    - generators:  
        # Generator named 'id' that counts up from 10
        - 'id': {type: 'number_sequence', start: 10}

- benchmark: # create new entities
    - generator_binds: {id: id}
    - name: "Create person"
    - url: {template: "/api/person/$id/"}
    - warmup_runs: 0
    - method: 'PUT'
    - headers: {'Content-Type': 'application/json'}
    - body: {template: '{"first_name": "$firstname","id": "$id","last_name": "$lastname","login": "test-login-$id"}'}
    - 'benchmark_runs': '1000'
    - output_format: csv
    - metrics:
        - total_time: total
        - total_time: mean

```

Currently, templating is only supported for the request body and URL.
There are technical challenges adding it everywhere, but plans to add it where needed to other options.

# Extractors Basics
**TBD** when features are frozen. 

# Validation Basics
**TBD** when features are frozen. 

# Lifecycles Of Different Operations
## TestSet Execution Lifecycle
1. Parse command line arguments
2. Parse YAML, reading top-level imports and building TestSets
3. Execute TestSets:
    1. Generate a Context for each test set, populated with generators and variables defined in the TestConfig
    2. Run each test in the test set, using the context, per the test lifecycle below
        * Print failures as they occur
    3. Add statistics from that test to information for that test's group
    4. Run benchmarks in the test set, writing results to files
4. Print out collected test results, grouped by the test group name
5. Exit, returning response code with number of failed tests

## General Test Lifecycle
1. Update context before test (method update_context_before in the Test)
    1. Bind variables defined in the test into the context
    2. Bind generator values defined for that test into the context
2. Templating: realize() final version for that test, reading lazy-loaded files
3. Configure a Curl call, using info from the test and its configure_curl call
4. IF interactive mode: print info and wait for response
5. Execute the curl call
6. Update context after the test (extraction)
7. Run validators
8. Construct and return a TestResponse()

## General Benchmark Lifecycle
1. Pre-processing (set up to store metrics efficiently)
2. Warmup, runs *warmup_runs* times
    1. Update context before test (variable and generator binding) 
    2. Realize test templating
    3. Reconfigure a Curl call (curl objects are reused if possible)
    4. Run Curl
3. Benchmarking, runs *benchmark_runs* times
    1. Update context before test (variable and generator binding) 
    2. Realize test templating
    3. Reconfigure a Curl call (curl objects are reused if possible)
    4. Run Curl
    5. Collect metrics (adding to arrays)
4. Postprocessing: analyze benchmark results, condense arrays, and generate a BenchmarkResult object

###Key notes about benchmarks: 
* Benchmarks do as little as possible: they do NOT run validators or extractors
* HTTP response bodies are not stored, to get the most accurate result possible
* They do NOT currently check HTTP response codes (this may be added later)
* Benchmarks track a static failure count, to account for network issues
* Benchmarks will try to optimize out as much templating as they can safely. 

# Generators Listing
List of all generators and their configuration elements (required, optional, and meaning).

## env_variable
Read an environment variable

### Configuration elements:
- variable_name: environment variable name, without prefix
 
### Example:
EXAMPLe here


## env_string


## number_sequence

### Configuration Elements:

### Example:
```yaml
---
- config:
    - testset: "Benchmark tests using test app"
    - generators:
        - 'id': {type: 'number_sequence', start: 10}

- benchmark: # create entity
    - generator_binds: {id: id}
    - name: "Create person"
    - url: {template: "/api/person/$id/"}
    - method: 'PUT'
    - headers: {'Content-Type': 'application/json'}
    - body: {template: '{"first_name": "Gaius","id": "$id","last_name": "Baltar","login": "login$id"}'}
    - metrics:
        - total_time: total
        - total_time: mean
```



  Name      |     Type      |        Arguments
------------|---------------|-------------------
number_sequence | sequence of numbers in order | 'start': first value, 'increment': amount to change by
env_variable    | value of environment variable | 
env_string      |  string with environment variable substitution done | string: the string to substitute
random_int | random numbers | none
random_text | random characters from character set | 


