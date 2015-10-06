# Build
cd docker
docker build -t pyresttest-build-ubuntu-14:0.1-SNAPSHOT -f Dockerfile-ubuntu-14 .
docker build -t pyresttest-build-centos6:0.1-SNAPSHOT -f Dockerfile-centos6 .

# Test images and if they pass, tag appropriately
docker run -it --rm pyresttest-build-ubuntu-14:0.1-SNAPSHOT python /tmp/verify_image.py
if [ $? -ne 0 ]; then
    exit 1
fi
docker tag pyresttest-build-ubuntu-14:0.1-SNAPSHOT pyresttest-build-ubuntu-14:0.1

docker run -it --rm pyresttest-build-centos6:0.1-SNAPSHOT python /tmp/verify_image.py
if [ $? -ne 0 ]; then
    exit 1
fi
docker tag pyresttest-build-centos6:0.1-SNAPSHOT pyresttest-build-centos6:0.1