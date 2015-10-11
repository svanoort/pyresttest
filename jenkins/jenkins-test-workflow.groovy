def testEnv = docker.image('pyresttest-build-ubuntu-14:latest')
def testEnv26 = docker.image('pyresttest-build-centos6:latest')

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
  git url: "$repo", branch: "$branch"
  stage 'Unit Test ubuntu-python27'
  doTest(testEnv, "python -m unittest discover -s pyresttest -p 'test_*.py'",  'python pyresttest/functionaltest.py', 'bash test_use_extension.sh')

  stage 'Unit Test centos6-python26'
  doTest(testEnv26, "python -m discover -s pyresttest -p 'test_*.py'",  'python pyresttest/functionaltest.py', 'bash test_use_extension.sh')
}

// Test Python 3 support, which *currently does not work*
// def testEnvPython3 = docker.image('pyresttest-build-centos6:latest')
//envRuns['ubuntu-python3'] = {node {
//  doTest(testEnvPython, "python3 -m discover -s pyresttest -p 'test_*.py'",  'python3 pyresttest/functionaltest.py',
//     "python3 pyresttest/resttest.py https://api.github.com extension_use_test.yaml --import_extensions 'sample_extension'")
//}}
