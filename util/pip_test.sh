#!/bin/bash
# Test Pip install/uninstall works okay
sudo pip install -i https://testpypi.python.org/pypi pyresttest

# Test installed
if [ -f '/usr/local/bin/resttest.py' ];
then
   echo "Runnable script installed okay"
else
   echo "ERROR: Runnable script DID NOT install okay"
fi

if [ -d '/usr/local/lib/python2.7/dist-packages/pyresttest/' ];
then
   echo "Library install okay"
else
   echo "ERROR: Library install DID NOT install okay"
fi

# Test script runs
resttest.py https://github.com ../simple_test.yaml
if [$? -ne 0]; then
    echo 'ERROR: Runnable script failed to execute okay testing GitHub query'
fi

# Test uninstall is clean
sudo pip uninstall -y pyresttest

if [ -f '/usr/local/bin/resttest.py' ];
then
   echo "ERROR: Runnable script for resttest.py did non uninstall"
else
   echo "Runnable script uninstalled okay"
fi

if [ -d '/usr/local/lib/python2.7/dist-packages/pyresttest/' ];
then
   echo "ERROR: Library install DID NOT uninstall okay"
else
   echo "Library uninstall okay"
fi