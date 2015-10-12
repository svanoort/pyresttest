# Blessings and Mistakes

Herein lies a chronicle of the consequences of good and bad design/implementation decisions, that others may learn more easily what this project taught the hard way. 

## Bad:
* Using flatten_dictionaries to handle invalid duplicate values in configs causes more grief than it saves
  - Hides user error where they can't even log errors
  - Very hard to change default behavior because rather than iterating through data, it is simply *lost*
* Long, procedural-style methods *hurt* to refactor and test
    - Parsing with the python equivalent of a switch statement is *awful* to work with
    - Execution pipelines with the full path in the method (run_test, run_testset, run_benchmark) are easy to write, hard to extend, test, or debug
* Edge cases in HTTP standards (example duplicate header) that could have been avoided
* Not making enough use of CI, Docker, or virtualenvs earlier: issues with python 2.6 vs. 2.7 vs. 3 compatibility that were hard to see and could have been handled earlier
* Libraries: I think it would have been smart to fork into two versions: a lightweight smoketesting core (basic execution only) and a heavier, dependency-laden version for benchmarking and more detailed testing.

## Good:
* Use of the integrated Django mini-test app made it *really easy* to construct full end-to-end tests and found countless suble mistakes that unittests won't
* Refactoring to use registry/factory pattern for validators, generators, comparators, extractors
    - Made it super easy to add header validation
    - Easy to test, easy to fork/extend, just plain nice
* PyCurl: I know people prefer requests, but pycurl is *really* powerful, fast, and runs everywhere. It's a good match for complex cases too. 
* YAML: the gift that keeps on giving vs. JSON or XML.  A pleasure to work with, especially via pyyaml