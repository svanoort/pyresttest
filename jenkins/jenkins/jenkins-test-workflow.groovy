def testEnv = docker.image('pyresttest-build-ubuntu-14:0.1')
def testEnv26 = docker.image('pyresttest-build-centos6:0.1')

// Run unit/functional/additional tests on given image
def doTest(imageName, unitTestCommand, functionalTestCommand, additionalTestScript) {
  imageName.inside() {
    git url: "$repo", branch: "$branch"
    dir('pyresttest') {
      sh unitTestCommand
      sh functionalTestCommand
      sh additionalTestScript
    }
  }
}

// Define the environments and specific test syntax for each
def env_runs = [:]
env_runs['ubuntu-python27'] = node {
  doTest(testEnv, "python -m unittest discover -s pyresttest -p 'test_*.py'",  'python pyresttest/functionaltest.py', 'bash test_use_extension.sh')
}

env_runs['centos6-python26'] = node {
  doTest(testEnv26, "python -m discover -s pyresttest -p 'test_*.py'",  'python pyresttest/functionaltest.py', 'bash test_use_extension.sh')
}

parallel env_runs

// Test Python 3 support, which *currently does not work*
//node {
//  doTest(testEnv, "python3 -m discover -s pyresttest -p 'test_*.py'",  'python3 pyresttest/functionaltest.py',
//     "python pyresttest/resttest.py https://api.github.com extension_use_test.yaml --import_extensions 'sample_extension'")
//}
