// Dockerized unit test flow for PyRestTest
// Takes parameters 'repo' (git URL) and 'branch' (git branch)

// Run unit/functional/additional tests on given image
def doTest(imageName, unitTestCommand, functionalTestCommand, additionalTestScript) {
  imageName.inside() {

    dir('pyresttest') {
      sh unitTestCommand
      sh functionalTestCommand
      sh additionalTestScript
    }
  }
}

node {
  // Run in one node, but use docker multiple times with same repo
  // This is run in sequence because otherwise the functional tests
  //   will touch the same files and break

  git url: "$repo", branch: "$branch"

  stage 'Build docker images'
  sh 'docker/build.sh'
  def testEnv = docker.image('pyresttest-build-ubuntu-14:latest')
  def testEnv26 = docker.image('pyresttest-build-centos6:latest')
  def testEnvPy3 = docker.image('pyresttest-build-python3')

  stage 'Unit Test ubuntu-python27'
  doTest(testEnv, "python -m unittest discover -s pyresttest -p 'test_*.py'",
    'python pyresttest/functionaltest.py',
    'bash test_use_extension.sh')

  stage 'Unit Test centos6-python26'
  doTest(testEnv26, "python -m discover -s pyresttest -p 'test_*.py'",
    'python pyresttest/functionaltest.py',
    'bash test_use_extension.sh')

  stage 'Unit Test debian-wheezy using python-3.4.3'
  doTest(testEnvPy3, "python3 -m unittest discover -s pyresttest -p 'test_*.py'",
    'python3 pyresttest/functionaltest.py',
    'bash test_use_extension.sh')
}