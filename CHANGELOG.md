# Changelog

## 1.7.1 Mon Mar 15 23:05:00 2016 -0400
**Bugfixes:**
* Fix JSONschema extension in Python 3, and add test coverage for it
  - Thanks to @BastienAr for reporting it: https://github.com/svanoort/pyresttest/issues/173

## 1.7.0 Sat Mar 06 14:30:00 2016 -0400
**Features:**
* Unicode support epic: fix handling of request body and a whole raft of smaller fixes + more tests: https://github.com/svanoort/pyresttest/issues/104
* ALPHA: Python 3 support - all tests now pass!
* JMESPath extractor: a proper JSON query syntax to use in validation
  - Thanks to @marklz for his contribution (significant effort), tracked in https://github.com/svanoort/pyresttest/pull/156
* JsonPath_Mini extractor supports ability to return the root response object now with the "." syntax -- thanks for the PR! https://github.com/svanoort/pyresttest/pull/106
* Allow for smarter URL creation from fragments: https://github.com/svanoort/pyresttest/issues/118
* Reuse Curl handles in tests, which improves test performance with connection reuse and DNS caching:
  - https://github.com/svanoort/pyresttest/pull/160
* Add terminal output coloring for pass/pail (able to turn off via cmdline)
  - Thanks to @lerrua for his PRs  https://github.com/svanoort/pyresttest/pull/125 https://github.com/svanoort/pyresttest/pull/141
* Switch from legacy distutils for install to setuptools:
  - Thanks @lerrua for the PR - https://github.com/svanoort/pyresttest/pull/122

**Bugfixes:**
* Whole raft of bugfixes around Unicode handling and request/response bodies
* Fix bug in parsing of the curl_option argument - thanks to @jcelliot for noticing this
  - Noted in https://github.com/svanoort/pyresttest/issues/138
* Fix HTTP PATCH method configuration - many thanks to @lerrua for his PR!
  - Noted in https://github.com/svanoort/pyresttest/issues/117
  - Fixed in https://github.com/svanoort/pyresttest/pull/129
* Fix the HTTP DELETE use with a body, which could not be tested
  - Thanks to @spradeepv for the pull request: https://github.com/svanoort/pyresttest/pull/165
* Fix HTTP HEAD method configuration 
  - Thanks to @ksramchandani for reporting issues that triggered an investigation (different root cause) in https://github.com/svanoort/pyresttest/issues/117
* Fix Django testing breakage by locking to a functioning version
  - e39d156b56962e86a0054ba11304eb37f8a3b46d and e731ebaee6f4926e7c42fb551af8ff4930a7127b

**Known Issues / Back-Compatibility:**
* Headers are returned from tests as unicode key, value pairs now

## 1.6.0 Mon Oct 12 07:30:00 2015 -0400
**Features:**
* BETA: Add a type testing comparator to assist with validating request/header bodies
  - Issue: https://github.com/svanoort/pyresttest/issues/90 (derived from online feedback)
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
* Fix issue with use of curl WRITEDATA opt on CentOS 6 / Python 2.6 (use writefunction instead)
* Fix/document installation issues with dependencies

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
