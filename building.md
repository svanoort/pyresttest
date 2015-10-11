# How to build

There are two options for how to work with code

## Key scripts:
- Unit + functional tests: run_tests.sh
- Coverage Test: coverage.sh (result in htmlconv/index.html)

## Conventions
- All non-functional unit tests (runnable without a server) start with 'test_'

## Environments
1. Local (native) python (Linux or Mac)
  - You'll need to pip install the following packages:
    + pycurl
    + pyyaml
    + mock
    + django==1.6.5 (for functional testing server)
    + django-tastypie (for functional testing server)
    + discover (if on a python 2.6 system)
  - Avoid a virtualenv unless you *very carefully* set it up for pycurl use (it may not find libcurl)

2. Docker: see the docker folder, we have preconfigured images for a *stable, clean verified* dev/test environment 
  1. (sudo) 'build.sh' will build docker images and verify the environment
    - pyresttest-build-centos6 acts as the python 2.6 / RPM-based distro environment
    - pyresttest-build-ubuntu-14 acts as the python 2.7 and apt-based distro environment
    - pyresttest-build-python3 acts as a clean testbed for work on python3 compatibility
  2. After building you can use them as dev environments in volumes:
    - (sudo) docker run -v `PWD`:/tmp/pyresttest -it --rm pyresttest-build-centos6 /bin/bash
    - (sudo) docker run -v `PWD`:/tmp/pyresttest -it --rm pyresttest-build-ubuntu-14 /bin/bash
  3. OR just run the images and clone the repo from within them:
    1. (sudo) docker run -it --rm pyresttest-build-ubuntu-14 /bin/bash
    2. Inside container: cd /tmp && git clone https://github.com/svanoort/pyresttest.git
    3. Do your coding and commit/push, etc

## Releasing
Release tooling requires its own special goodies.  The docker images have it all baked in, for convenience's sake.

1. Tar (for packaging distributions)
2. For CentOS 6, rpm-build