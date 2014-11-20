Advanced Guide For PyRestTest:
==========

This provides a more detailed guide to using the advanced features of PyRestTest.
Specifically **generators**, **variable binding,** **data extraction,** and **content validators.**

# Templating and Context Basics
- Tests and benchmarks may use variables to template out configuration dynamically.
- Templating is performed using basic [Python string templating](https://docs.python.org/2/library/string.html#template-strings).  
- Templating uses variables contained in a context, and **templates are evaluated freshly** for each test run or benchmark iteration
- Contexts are either passed into a test, or created in the text if not supplied
- **Contexts are persistent within a TestSet. Once a variable is set, it can be used in all following tests**
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
Extractors are query-based ways to extract some part of an HTTP response body for use.

This can be used as part of a validator or to capture values to a context variable for later use. 

Current extractors are limited, but the functions are pluggable -- it is very easy to add full JsonPath, regex matching, xpath, xquery, etc and use them in your testing.

**An extractor definition looks like this:**
```yaml
extractor_name: extractor_configuration
```
Extractor configuration may be a simple string query, a templated string, or a more complex object.  It's completely up to the extractor parsing function how to handle this.

## Extractor: jsonpath_mini
The basic 'jsonpath_mini' extractor provides a very limited [JsonPath](http://goessner.net/articles/JsonPath/)-like implementation to grab data from JSON, with no external library dependencies.

The elements of this  syntax are a list of keys or indexes, descending down a tree, seperated by periods. Numbers are assumed to be array indices.

**Example:**
Given this JSON:
```json
{
    "thing":{"foo":"bar"},
    "link_ids": [1, 2, 3, 4],
    "person":{
        "firstname": "Bob",
        "lastname": "Smith",
        "age": 17
    }
}
```

- This query: 'person.lastname'
Will return:  "Smith"

- This query: 'person.is_a_ninja'
Will return: NOTHING (None object) -- that key is not defined for 'person'.

- This query: 'link_ids.1'
 Will return: 2

- This query: 'thing'
Will return: {"foo":"bar"}

- This query: 'thing.0'
Will return: None -- trick question, 'thing' is not an array!

Super simple, super basic, but it actually will cover a lot of useful cases. 

**This extractor also supports templating:**
```yaml
jsonpath_mini: {template: $keyname.age}
```

- If the context variable 'keyname' is set to 'person', this will return 17.
- If it is set to 'thing', then it will return nothing (because the 'thing' object lacks an 'age' key)


# Validation Basics
Validators test response bodies for correctness.  They perform a test on the response body, with context supplied, and return a value that will evaluate to boolean True or False. 

Optionally, validators can return a ValidationFailure which evaluates to False, but supplies additional information. 

## Current Validators:
### Extract and test value:
- **Name:** 'extract_test'
- **Description:** run an extractor to extract a value from the body and test it using a function.
- **Arguments:**
    + (extractor): an extractor definition, see above, named by extractor type
    + test: a test function to apply, which returns true or false (see list below)

- **Examples:**
```yaml
- validators:
    # Test key does not exist
    - extract_test: {jsonpath_mini: "key_should_not_exist",  test: "not_exists"}
```

#### Test Functions
'exists', 'not_exists' - check if there's a value or not


### Extract And Compare:
- **Name:** 'comparator' or 'compare'
- **Description:** run an extractor and compare results to expected value
- **Arguments:**
    + (extractor): an extractor definition, see above, named by extractor type
    + comparator: a comparator function to apply, which returns true or false (see list below)
    + expected: value is:
        + expected value (a literal) 
        + a template: {template: 'template_string'} - gotcha here, you need to use 'str_eq' comparator if you want to template numeric values.
        + an extractor definition. Yes, you can compare two parts of the response body.

- **Examples:**
```yaml
- validators:
     # Check the user name matches
     - compare: {jsonpath_mini: "user_name", comparator: "eq", expected: 'neo'}
     
     # Check the total_count key has value over 10
     - compare: {jsonpath_mini: "total_count", comparator: "gt", expected: 10}
     
     # Check the user's login
     - compare: {jsonpath_mini: "total_count", comparator: "gt", expected: }
```


#### Comparator Functions:
| Name(s)                                      |                Description                | Details for comparator(A, B)                                           |
|----------------------------------------------|:-----------------------------------------:|------------------------------------------------------------------------|
| 'count_eq' | Check count of elements equals value      | length(A) == B                                                         |
| 'lt', 'less_than':                           | Less Than                                 | A < B                                                                  |
| 'le', 'less_than_or_equal'                   | Less Than Or Equal To                     | A <= B                                                                 |
| 'eq', 'equals'                               | Equals                                    | A == B                                                                 |
| 'str_eq'                                     | Values are Equal When Converted to String | str(A) == str(B) -- useful for comparing templated numbers/collections |
| 'ne', 'not_equals'                           | Not Equals                                | A != B                                                                 |
| 'ge', 'greater_than_or_equal'                | Greater Than Or Equal To                  | A >= B                                                                 |
| 'gt', 'greater_than'                         | Greater Than                              | A > B                                                                  |



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
Example here


