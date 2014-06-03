pyresttest
==========

Python scripts for testing REST services.

# License
Apache License, Version 2.0

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

# Troubleshoot

## Cannot find argparse
```
sudo su -
easy_install argparse
exit
```
