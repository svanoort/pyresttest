# Build
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

UBUNTU_14_VERSION=0.2
CENTOS6_VERSION=0.2
PYTHON3_VERSION=0.3

docker build -t pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT ./ubuntu14-py27
docker build -t pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT ./centos6-py26
docker build -t pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT ./python3

# Test images and if they pass, tag appropriately
docker run -it --rm pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT python /tmp/verify_image.py
if [ $? -ne 0 ]; then  # Test failed, remove the built image and exit with error
    docker rmi pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT
    exit 1
fi
docker tag -f pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION
docker tag -f pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT pyresttest-build-ubuntu-14:latest
docker rmi pyresttest-build-ubuntu-14:$UBUNTU_14_VERSION-SNAPSHOT

docker run -it --rm pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT python /tmp/verify_image.py
if [ $? -ne 0 ]; then  # Test failed, remove the built image and exit with error
    docker rmi pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT
    exit 1
fi
docker tag -f pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT pyresttest-build-centos6:$CENTOS6_VERSION
docker tag -f pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT pyresttest-build-centos6:latest
docker rmi pyresttest-build-centos6:$CENTOS6_VERSION-SNAPSHOT

docker run -it --rm pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT python3 /tmp/verify_image.py
if [ $? -ne 0 ]; then  # Test failed, remove the built image and exit with error
    docker rmi pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT
    exit 1
fi
docker tag -f pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT pyresttest-build-python3:0.2
docker tag -f pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT pyresttest-build-python3:latest
docker rmi pyresttest-build-python3:$PYTHON3_VERSION-SNAPSHOT