# Build
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

docker build -t pyresttest-build-ubuntu-14:0.1-SNAPSHOT -f Dockerfile-ubuntu-14 .
docker build -t pyresttest-build-centos6:0.1-SNAPSHOT -f Dockerfile-centos6 .
docker build -t pyresttest-build-python3:0.1-SNAPSHOT -f Dockerfile-python3 .

# Test images and if they pass, tag appropriately
docker run -it --rm pyresttest-build-ubuntu-14:0.1-SNAPSHOT python /tmp/verify_image.py
if [ $? -ne 0 ]; then
    exit 1
fi
docker tag -f pyresttest-build-ubuntu-14:0.1-SNAPSHOT pyresttest-build-ubuntu-14:0.1

docker run -it --rm pyresttest-build-centos6:0.1-SNAPSHOT python /tmp/verify_image.py
if [ $? -ne 0 ]; then
    exit 1
fi
docker tag -f pyresttest-build-centos6:0.1-SNAPSHOT pyresttest-build-centos6:0.1

docker run -it --rm pyresttest-build-python3:0.1-SNAPSHOT python3 /tmp/verify_image.py
if [ $? -ne 0 ]; then
    exit 1
fi
docker tag -f pyresttest-build-python3:0.1-SNAPSHOT pyresttest-build-python3:0.1