Jenkins workflows for testing

* Each flow describes necessary parameters at top, if run directly

[jenkins-build-images.groovy](jenkins-build-images.groovy): Run directly to build docker images for unit testing, equivalent to the [docker build.sh](../docker/build.sh) script
[jenkins-test-workflow.groovy](jenkins-test-workflow.groovy):  Direct run flow - runs unit tests using the Docker images above
[lib-jenkins-installtest.groovy](jenkins-new-installtest.groovy): Library of functions to do installation & functional testing in Docker environments

* Unit tests exercise the raw code itself
* Installer tests exercise the setup protocols, path handling, and import handling
