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

          String argument = 'bash -c \'set -o pipefail; '+cmd+" | tee \"testresults/$fileName-$name"+'.log'+'" \''
          sh argument
        }
      } catch (Exception ex) {
        archive("testresults/$fileName"+'*.log')
        throw ex
      }
      archive("testresults/$fileName"+'*.log')
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
  sh 'rm -rf testresults'
  sh 'mkdir testresults'
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

node {
  // Build the base sudo images
  stage 'Build the sudo images for installation'
  sh 'rm -rf sudo-images'
  dir('sudo-images') {
    git url:'https://github.com/jenkinsci/packaging.git', branch:'master'
    sh 'docker/build-sudo-images.sh'
  }

  // Build the py3 sudo image.
  sh 'rm -rf py3-sudo'
  dir('py3-sudo') {
    git url:'https://github.com/svanoort/pyresttest.git', branch:'installation-test-and-fix'
    sh 'sed -i-e "s#@@MYUSERID@@#`id -u`#g" docker/sudo-python3/Dockerfile'
    sh 'docker build -t sudo-python3:3.4.3-wheezy docker/sudo-python3'
  }

  // Removing the PyRestTest directory has to be done inside a container with sudo
  // Because otherwise sudo use might leave remnants that Jenkins can't remove
  docker.image('sudo-python3:3.4.3-wheezy').inside() {
    sh 'sudo rm -rf pyresttest'
  }
  dir('pyresttest') {
    git url:'https://github.com/svanoort/pyresttest.git', branch:branch

    //Images with sudo, python and little else, for a bare installation
    String basePy26 = 'sudo-centos:6'
    String basePy27 = 'sudo-ubuntu:14.04'
    String basePy34 = 'sudo-python3:3.4.3-wheezy'

    // Base installs, including pycurl since it almost never installs right
    String installAptPybase = 'sudo apt-get update && sudo apt-get install -y python-pip python-pycurl'
    String installAptPybasePy3 = 'sudo apt-get update'  // Comes with python 3, pip using it
    String installYumPybase = 'sudo rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm && sudo yum install -y python-pip python-pycurl'

    // Libs for direct run of library
    String install_libs = 'sudo pip install pyyaml'
    String install_libs_py3 = 'sudo pip install pycurl pyyaml future'

    // Install pyresttest directly from repo
    String pyr_install_direct = 'sudo python setup.py install'

    // Tests
    String testBasic1 = "resttest.py --help | grep 'Usage' "
    String testBasic2 = "pyresttest --help | grep 'Usage' "
    String testImport = 'python -c "from pyresttest import validators"'  // Try importing
    String testApiDirect = "python pyresttest/resttest.py https://api.github.com examples/github_api_smoketest.yaml"
    String testApiUtil = "pyresttest https://api.github.com examples/github_api_smoketest.yaml"

    // Preinstall libs and run/use library from repo clone
    def test_clone_names = ['setup', 'install-libs', 'import-test', 'functional-gh-test']
    def testPy26_clone = [basePy26, [installYumPybase, install_libs, testImport, testApiDirect]]
    def testPy27_clone = [basePy27, [installAptPybase, install_libs, testImport, testApiDirect]]
    def testPy34_clone = [basePy34, [installAptPybasePy3, install_libs_py3, testImport, testApiDirect]]

    // Direct setup.py install
    def test_direct_names = ['setup', 'install-pyresttest', 'test-cmdline1', 'test-cmdline2', 'import-test', 'functional-gh-test', 'test-functional-cmdline']
    def testPy26_directInstall = [basePy26, [installYumPybase,    pyr_install_direct, testBasic1, testBasic2, testApiDirect, testApiUtil]]
    def testPy27_directInstall = [basePy27, [installAptPybase,    pyr_install_direct, testBasic1, testBasic2, testApiDirect, testApiUtil]]
    def testPy34_directInstall = [basePy34, [installAptPybasePy3, pyr_install_direct, testBasic1, testBasic2, testApiDirect, testApiUtil]]

    stage 'Basic Test: running from repo with preinstalled libs'
    execute_install_testset([testPy27_clone, testPy26_clone, testPy34_clone], test_clone_names)

    stage 'Basic Test: running from setup.py install'
    execute_install_testset([testPy27_directInstall, testPy26_directInstall, testPy34_directInstall], test_direct_names)

    // TODO Add ability to run all tests before showing failures
    // TODO Functional test using content-test against a docker container running the Django testapp (with a docker link)
    // TODO TestPyPi install & test
    // TODO VirtualEnv test
    // TODO pip install -e mode, perhaps???
  }
}