// Test installing pyresttest
// @param (String) branch Branch to clone and install from


// Replace colons in image with hyphens and append text
String convertImageNameToString(String imageName, String append="") {
    return (imageName+append).replaceAll(':','-')
}

/** Runs a series of shell commands inside a docker image
* The output of each command set is saved to a specific file and archived
* Errors are propagated back up the chain.
* @param imageName docker image name to use (must support sudo, based off the sudoable images)
* @param shellCommands List of (string) shell commands to run within the container
* @param stepNames List of names for each shell command step, optional
*                    (if not supplied, then the step # will be used)
*/
def run_shell_test(String imageName, def shellCommands, def stepNames=null) {
  withEnv(['HOME='+pwd()]) { // Works around issues not being able to find docker install
    def img = docker.image(imageName)
    def fileName = convertImageNameToString(imageName,"-testOutput-")
    img.inside() {  // Needs to be root for installation to work
      try {
        for(int i=0; i<shellCommands.size(); i++) {
          String cmd = shellCommands.get(i)
          def name = (stepNames != null && i < stepNames.size()) ? stepNames.get(i) : i

          // Workaround for two separate and painful issues
          // One, in shells, piped commands return the exit status of the last command
          // This means that errors in our actual command get eaten by the success of the tee we use to log
          // Thus, failures would get eaten and ignored.
          // Setting pipefail in bash fixes this by returning the first nonsuccessful exit in the pipe

          // Second, the sh workflow step often will use the default posix shell
          // The default posix shell does not support pipefail, so we have to invoke bash to get it

          String argument = 'bash -c \'set -o pipefail; '+cmd+" | tee testresults/$fileName-$name"+'.log'+' \''
          sh argument
        }
      } catch (Exception ex) {
        throw ex
      } finally {
        archive("testresults/$fileName"+'*.log')
      }
    }
  }
}


/** Install tests are a set of ["dockerImage:version", [shellCommand,shellCommand...]] entries
* They will need sudo-able containers to install
* @param stepNames Names for each step (if not supplied, the index of the step will be used)
*/
def execute_install_testset(def coreTests, def stepNames=null) {
  // Within this node, execute our docker tests
  def parallelTests = [:]

  for (int i=0; i<coreTests.size(); i++) {
    def imgName = coreTests[i][0]
    def tests = coreTests[i][1]
    parallelTests[imgName] = {
      try {
       run_shell_test(imgName, tests, stepNames)
      } catch(Exception e) {
        // Keep on trucking so we can see the full failures list
        echo "$e"
        error("Test for $imgName failed")
      }
    }
  }
  parallel parallelTests
}

// Flows
stage 'Build Images'
build job: 'build-docker-images-wf', parameters: [[$class: 'StringParameterValue', name: 'branch', value: 'master']]

//Images with sudo, python and little else, for a bare installation
String basePy26 = 'sudo-centos:6'
String basePy27 = 'sudo-ubuntu:14.04'
//String basePy34 = 'python:3.4.3-wheezy'


node {
  // Build the base sudo images
  sh 'rm -rf sudo-images'
  dir('sudo-images') {
    git url:'https://github.com/jenkinsci/packaging.git', branch:'master'
    sh 'docker/build-sudo-images.sh'
  }

  // Build the py3 sudo image.
  /*sh 'rm -rf py3-sudo'
  dir('py3-sudo') {
    git url:'https://github.com/svanoort/pyresttest.git', branch:'py3-installtest'
  }*/

  sh 'rm -rf pyresttest'
  dir('pyresttest') {
    git url:'https://github.com/svanoort/pyresttest.git', branch:'master'

    // Base installs, including pycurl since it almost never installs right
    String installAptPybase = 'sudo apt-get update && sudo apt-get install -y python-pip python-pycurl'
    String installYumPybase = 'sudo yum install -y python-pip python-pycurl'

    // Libs for direct run of library
    String install_libs = 'sudo pip install pyyaml'
    String install_libs_py3 = 'sudo pip install pyyaml future'

    // String install_py3_pybase = 'sudo yum install -y python-pip python-pycurl && sudo pip install future pyyaml'
    String pyr_install_direct = 'sudo python setup.py install'
    String pyr_install_direct_py3 = 'sudo python3 setup.py install'

    // Tests
    String testBasic1 = "resttest.py 2>/dev/null | grep 'Usage' "
    String testBasic2 = "pyresttest 2>/dev/null | grep 'Usage' "
    String testImport = "python -c 'from pyresttest import validators'"  // Try importing
    String testImportPy3 = "python3 -c 'from pyresttest import validators'"
    String testApiDirect = "python pyresttest/resttest.py https://api.github.com examples/github_api_smoketest.yaml"
    String testApiDirectPy3 = "python3 pyresttest/resttest.py https://api.github.com examples/github_api_smoketest.yaml"
    String testApiUtil = "resttest.py https://api.github.com examples/github_api_smoketest.yaml"

    def testPy26_clone = [basePy26, [installYumPybase, basicTest1, basicTest2, importTest, apiTest]]
    def testPy27_clone = [basePy27, [installAptPybase, basicTest1, basicTest2, importTest, apiTest]]
    def testPy26_directInstall = [basePy26, [installYumPybase, pyr_easyinstall, basicTest1, basicTest2, apiTest]]
    def testPy27_directInstall = [basePy27, [installAptPybase, pyr_easyinstall, basicTest1, basicTest2, apiTest]]

    def test_names = ['setup', 'test resttest.py script', 'test pyrestest script', 'import test', 'functional github test']

    stage 'Basic Test: Ubuntu 14.04/Python 2.7'
    execute_install_testset(testPy27_clone, test_names)
    execute_install_testset(testPy27_directInstall, test_names)

    stage 'Basic Test: CentOS6/Python 2.6'
    execute_install_testset(testPy26_clone, test_names)
    execute_install_testset(testPy26_directInstall, test_names)

    // TODO python 3 tests

    // TODO Functional test using content-test against a docker container running the Django testapp (with a docker link)
    // TODO TestPyPi install & test
    // TODO VirtualEnv test
  }
}

