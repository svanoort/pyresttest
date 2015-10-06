#!/bin/bash
docker build -t pyresttest-build-ubuntu-14:0.1 -f Dockerfile-ubuntu-14 .

docker build -t pyresttest-build-centos6:0.1 -f Dockerfile-centos6 .