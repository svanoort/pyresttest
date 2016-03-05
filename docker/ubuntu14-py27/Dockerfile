FROM ubuntu:14.04
MAINTAINER svanoort <samvanoort@gmail.com>

RUN apt-get update && apt-get install --no-install-recommends -y python python-pip python-pycurl tar git-core \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Python 2 and 3 dependencies
RUN pip install mock jmespath pyyaml django==1.6.5 django-tastypie==0.12.1

COPY verify_image.py /tmp/verify_image.py
RUN chmod a+rwx /tmp/verify_image.py