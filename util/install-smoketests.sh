# bdist will cause *issues*

# CentOS install script to test it
# docker run -it --rm -v `pwd`:/tmp/pyresttest centos:centos6 /bin/bash
rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
yum install -y python-pip
pip install -i https://testpypi.python.org/pypi pyresttest


#Interactive test to see if it works
resttest.py
python -c "import pyresttest"
pip show version pyresttest

# test (each returns exit code)
resttest.py 2>/dev/null | grep 'Usage'
pyresttest 2>/dev/null | grep 'Usage'
resttest.py https://api.github.com /tmp/pyresttest/github_api_smoketest.yaml


# Install on Ubuntu14
# docker run -it --rm -v `pwd`:/tmp/pyresttest ubuntu:14.04 /bin/bash
apt-get update && apt-get install -y python-pip
apt-get install python-pycurl
pip install -i https://testpypi.python.org/pypi --pre pyresttest

# Same tests
# Now we do the more involved tests using prebaked images with test server
# docker run -it --rm -v `pwd`:/tmp/pyresttest pyresttest-build-ubuntu-14:latest /bin/bash
# docker run -it --rm -v `pwd`:/tmp/pyresttest pyresttest-build-centos6:latest /bin/bash
python /tmp/pyresttest/pyresttest/testapp/manage.py testserver /tmp/pyresttest/pyresttest/testapp/test_data.json &
pyresttest http://localhost:8000 /tmp/pyresttest/pyresttest/content-test.yaml