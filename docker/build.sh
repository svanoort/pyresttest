#!/bin/bash
# Build and verify docker images for testing/developing pyresttest

set -x
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

UBUNTU_14_VERSION=0.5
CENTOS6_VERSION=0.5
PYTHON3_VERSION=0.6

docker build -t pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT ./ubuntu14-py27
docker build -t pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT ./centos6-py26
docker build -t pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT ./python3

# Test images and if they pass, tag appropriately
docker run -t --rm pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT python /tmp/verify_image.py
if [ $? -ne 0 ]; then  # Test failed, remove the built image and exit with error
    docker rmi pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT
    echo 'Ubuntu 14 build with python 2.7 failed'
    exit 1
fi
docker tag -f pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION
docker tag -f pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT pyresttest-build-ubuntu-14:latest
docker rmi pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT

docker run -t --rm pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT python /tmp/verify_image.py
if [ $? -ne 0 ]; then  # Test failed, remove the built image and exit with error
    docker rmi pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT
    echo 'CentOS6 build with python 2.6 failed'
    exit 1
fi
docker tag -f pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT pyresttest-build-centos6:$CENTOS6_VERSION
docker tag -f pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT pyresttest-build-centos6:latest
docker rmi pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT

docker run -t --rm pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT python3 /tmp/verify_image.py
if [ $? -ne 0 ]; then  # Test failed, remove the built image and exit with error
    docker rmi pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT
    echo 'Debian-wheezy build with python 3.4.3 failed'
    exit 1
fi
docker tag -f pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT pyresttest-build-python3:$PYTHON3_VERSION
docker tag -f pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT pyresttest-build-python3:latest
docker rmi pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT

# Build the sudo images for custom testing
cd "$(dirname "$0")"
sed -i .orig -e "s#@@MYUSERID@@#`id -u`#g" sudo-*/Dockerfile
docker build -t sudo-python3:3.4.3-wheezy sudo-python3