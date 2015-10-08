# Changelog

## 1.6.0-SNAPSHOT (pending release as 1.6.0)
**Features:**
* BETA: Allow setting custom Curl options with the curl_option_optionname field on tests
* BETA: support HTTP method types besides GET/PUT/POST/DELETE 
* BETA: support setting request body on all request types, if present
  - Allows (for example) DELETE methods that set a request body
  - Caveat: does not set length if 0
* raw_body extractor that returns the full HTTP response body
  -  Requested in: https://github.com/svanoort/pyresttest/pull/71
* Add test coverage script (uses 'coverage', which requires install)

**Bugfixes:**
* Fix bug with headers not being passed to extract_bind extrators, which caused: 
  - https://github.com/svanoort/pyresttest/issues/70
  - https://github.com/svanoort/pyresttest/issues/63
* Extractors did not raise an exception on failure: https://github.com/svanoort/pyresttest/issues/64

**Known Issues / Back-Compatibility:**
* Minor: generator letters/uppercase/lowercase are now always ASCII, not locale-aware
  - Driven by python 3 compatibility, and probably more "correct" but still a change
* Headers are now lists of (key, value) pairs, extractors need to be aware of this
    - *Will only be an issue for people using custom header extractors*
    - After some serious googling, as far as I can tell, nobody is using headers in custom extensions yet
    - This can be patched into a back-compatibile approach if it breaks anyone

**Misc:**
* Automation start (Jenkins setup, initial testing Dockerfiles) including 2.6 and 2.7 compat
* Dockerfiles to create build/test environments
* run_tests.sh now exits on first failure, and returns exit code (for automation)
  - In PR: https://github.com/svanoort/pyresttest/pull/82

## 1.5.0 - Released Tue Aug 11 10:54:29 2015 -0400

**Features**
* Command line argument --verbose to set verbose mode for PyRestTest
  - Thanks @netjunki for your PR! https://github.com/svanoort/pyresttest/pull/49
* A series of fixes to move towards Python3 support
    - Many thanks to @MorrisJobke for his assistances! https://github.com/svanoort/pyresttest/pull/59
* Add delay parameter to tests:
  - Thanks to @netjunki for the PR!  https://github.com/svanoort/pyresttest/pull/51
* Added option to print headers while running test via --print-headers option
  - Thanks to @netjunki for the contribution: https://github.com/svanoort/pyresttest/pull/56
* Add support to give an *absolute* URL in tests and use the --absolute-url argument to ignore command-line URL
  - Thanks to @Kesmy for the PR!  https://github.com/svanoort/pyresttest/pull/53

**Bugfixes:**
* Fix the not_equals/ne comparator 
  - Thanks to @Kesmy for the PR! https://github.com/svanoort/pyresttest/issues/54
* Fix vars not being passed correctly from command line
  - Thanks to @netjunki for the PR: https://github.com/svanoort/pyresttest/pull/50

**Back-compatibility breaks**
* None

## 1.4.0 - Released Mon May 25 12:34:23 2015 -0400
* Do not have good tracking this far back
