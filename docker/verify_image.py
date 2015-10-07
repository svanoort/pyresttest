#!/usr/bin/env/python

# Check that the docker image has what we need to run & build python
import yaml
import pycurl
import os
import django
import mock

mycurl = pycurl.Curl()
mycurl.close()

returnval = os.system('git --version > /dev/null')
assert returnval == 0