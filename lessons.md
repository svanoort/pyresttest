# Lessons

A walkthrough of good and bad decisions in building PyRestTest and their consequences.  Perhaps informative for others, and at the least interesting because of how it reflects growing knowledge of the python ecosystem. 

## Mistakes:
* Parsing configuration: using flatten_dictionaries to handle invalid duplicate values in configs causes more grief than it saves
  - Hides user errors where they can't even be logged in some cases
  - Very hard to change default behavior because rather than iterating through data, it is simply *lost*
  - Better done by using per-element calls in a streaming fashion (call a handler for each)
* Execution pipelines written in a long procedural style (run_test, run_testset, run_benchmark) are easy to write, hard to extend, test, or debug
    - Knew this going in, but didn't expect how much some methods (run_test, for example) would grow over time
    - Makes it very hard to do unit testing
* Parsing with the python equivalent of a switch statement is *awful* to work with, a registry/factory method system is easier
* Edge cases in HTTP standards (example: duplicate headers) that could have been avoided by better research
* Not making enough use of CI, Docker, or virtualenvs earlier: issues with python 2.6 vs. 2.7 vs. 3 compatibility that were hard to see and could have been handled earlier and less painfully
* Libraries: I think it would have been smart to fork into two versions: a lightweight smoketesting core (basic execution only) and a heavier, library-coupled version for benchmarking and more detailed testing.
  - This would have made it easier to keep the lean base for healthchecks/smoketests but also grow more featureful

## Smart Decisions
* Use of the integrated Django mini-app for functional testing made it *really easy* to construct full end-to-end tests and found countless subtle mistakes that unit tests won't
* Refactoring to use registry/factory pattern for validators, generators, comparators, extractors
    - Made it super easy to add header validation
    - Adding new comparators is a cinch
    - Easy to test, easy to fork/extend, just plain nice
* PyCurl: I know people prefer requests, but pycurl is *really* powerful, performant, and runs everywhere. It's a good match for complex cases too. 
* YAML: the gift that keeps on giving vs. JSON or XML.  A pleasure to work with, especially via pyyaml
* Use of the logging facilities: makes life so much easier
* Switching to use contexts instead of environment variables: cleaner, easier to debug
* Incorporating the jsonpath_mini extension from another contributor and keeping it working: a really good call, it's proving endlessly useful (if limited)
* Registerable extension system: rather proud of this, to be honest. It might grow to support more optional modules though.
* Run as a simple command line tool: YES.  Makes it so much easier to use.

# TBD
* Focus on default string.Template for templating over Jinja or a more complex option
  - Pro: portable, simple, fairly fast, easy to test / Con: limited features
* Not directly integrating with unittest or other test framework (going its own way)
  - Pro: more powerful, more flexible, superset of features / Con: more code, less consistent logging
