FROM python:3.4.3-wheezy
MAINTAINER svanoort <samvanoort@gmail.com>

RUN apt-get update && apt-get install --no-install-recommends -y git-core tar \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Python 2 and 3 dependencies, future is just for python 3 compat, sigh
RUN pip3 install pycurl jmespath jsonschema pyyaml django==1.6.5 django-tastypie==0.12.1 future

COPY verify_image.py /tmp/verify_image.py
RUN chmod a+rwx /tmp/verify_image.py