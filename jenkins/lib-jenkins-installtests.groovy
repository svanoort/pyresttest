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

/** Build the docker images needed for testing
* @param packagingBranch Jenkins packaging branch to use in building sudo images
* @param py3SudoBranch Python 3 branch to use in building the python 3 sudo branch
*/
void do_build_docker(String packagingBranch='master', String py3SudoBranch='master') {
  // Build the base sudo images
  stage 'Build the sudo images for installation'
  sh 'rm -rf sudo-images'
  dir('sudo-images') {
    git url:'https://github.com/jenkinsci/packaging.git', branch:packagingBranch
    sh 'docker/build-sudo-images.sh'
  }

  // Build the py3 sudo image.
  sh 'rm -rf py3-sudo'
  dir('py3-sudo') {
    git url:'https://github.com/svanoort/pyresttest.git', branch:py3SudoBranch
    sh 'sed -i-e "s#@@MYUSERID@@#`id -u`#g" docker/sudo-python3/Dockerfile'
    sh 'docker build -t sudo-python3:3.4.3-wheezy docker/sudo-python3'
  }
}



  //  sh "python pyresttest/testapp/manage.py testserver pyresttest/testapp/test_data.json &"
  //  sh "pyresttest http://localhost:8000 pyresttest/content-test.yaml"

// Test running the installation via cloning
void do_clone_run(String pyresttestBranch='master'){
  //Images with sudo, python and little else, for a bare installation
  String basePy26 = 'sudo-centos:6'
  String basePy27 = 'sudo-ubuntu:14.04'
  String basePy34 = 'sudo-python3:3.4.3-wheezy'

  // Base installs, including pycurl since it almost never installs right
  String installAptPybase = 'sudo apt-get install -y python-pip python-pycurl'
  String installAptPybasePy3 = 'sudo apt-get install -y python-pip'  // Should come with it, but just in case!
  String installYumPybase = 'sudo rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm && sudo yum install -y python-pip python-pycurl'

  // Libs needed to run pyresttest
  String install_libs = 'sudo pip install pyyaml'
  String install_libs_py3 = 'sudo pip install pycurl pyyaml future'
  String install_django_libs = 'sudo pip install "django==1.6.5" django-tastypie==0.12.1'

  // Tests
  String testBasic1 = "resttest.py --help | grep 'Usage' "
  String testBasic2 = "pyresttest --help | grep 'Usage' "
  String testImport = 'python -c "from pyresttest import validators"'  // Try importing
  String testApiDirect = "python pyresttest/resttest.py https://api.github.com examples/github_api_smoketest.yaml"
  String testApiUtil = "pyresttest https://api.github.com examples/github_api_smoketest.yaml"

  def test_clone_names = ['setup', 'install-libs', 'import-test', 'functional-gh-test']
  def testPy26_clone = [basePy26, [installYumPybase, install_libs, testImport, testApiDirect]]
  def testPy27_clone = [basePy27, [installAptPybase, install_libs, testImport, testApiDirect]]
  def testPy34_clone = [basePy34, [installAptPybasePy3, install_libs_py3, testImport, testApiDirect]]

  docker.image('sudo-python3:3.4.3-wheezy').inside() {
    sh 'sudo rm -rf pyresttest'
  }
  dir('pyresttest') {
    git url:'https://github.com/svanoort/pyresttest.git', branch:pyresttestBranch
    stage 'Basic Test: running from repo with preinstalled libs'
    execute_install_testset([testPy27_clone, testPy26_clone, testPy34_clone], test_clone_names)
  }
}

// Set up using setup.py install
void do_directinstall_test(String pyresttestBranch='master') {
  //Images with sudo, python and little else, for a bare installation
  String basePy26 = 'sudo-centos:6'
  String basePy27 = 'sudo-ubuntu:14.04'
  String basePy34 = 'sudo-python3:3.4.3-wheezy'

  // Base installs, including pycurl since it almost never installs right
  String installAptPybase = 'sudo apt-get install -y python-pip python-pycurl'
  String installAptPybasePy3 = 'sudo apt-get install -y python-pip'  // Should come with it, but just in case!
  String installYumPybase = 'sudo rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm && sudo yum install -y python-pip python-pycurl'

  // Libs needed to run pyresttest
  String install_libs = 'sudo pip install pyyaml'
  String install_libs_py3 = 'sudo pip install pycurl pyyaml future'
  String install_django_libs = 'sudo pip install "django==1.6.5" django-tastypie==0.12.1'

  // Tests
  String testBasic1 = "resttest.py --help | grep 'Usage' "
  String testBasic2 = "pyresttest --help | grep 'Usage' "
  String testImport = 'python -c "from pyresttest import validators"'  // Try importing
  String testApiDirect = "python pyresttest/resttest.py https://api.github.com examples/github_api_smoketest.yaml"
  String testApiUtil = "pyresttest https://api.github.com examples/github_api_smoketest.yaml"

  // Direct setup.py install
  String pyr_install_direct = 'sudo python setup.py install'
  def test_direct_names = ['setup', 'install-pyresttest', 'test-cmdline1', 'test-cmdline2', 'import-test', 'functional-gh-test', 'test-functional-cmdline']

  def testPy26_directInstall = [basePy26, [installYumPybase,    pyr_install_direct, testBasic1, testBasic2, testApiDirect, testApiUtil]]
  def testPy27_directInstall = [basePy27, [installAptPybase,    pyr_install_direct, testBasic1, testBasic2, testApiDirect, testApiUtil]]
  def testPy34_directInstall = [basePy34, [installAptPybasePy3, pyr_install_direct, testBasic1, testBasic2, testApiDirect, testApiUtil]]

  docker.image('sudo-python3:3.4.3-wheezy').inside() {
    sh 'sudo rm -rf pyresttest'
  }
  dir('pyresttest') {
    git url:'https://github.com/svanoort/pyresttest.git', branch:pyresttestBranch
    stage 'Basic Test: running from setup.py install'
    execute_install_testset([testPy27_directInstall, testPy26_directInstall, testPy34_directInstall], test_direct_names)
  }
}

// Development mode install via pip -e mode
void do_pip_develop_tests(String pyresttestBranch='master') {
  //Images with sudo, python and little else, for a bare installation
  String basePy26 = 'sudo-centos:6'
  String basePy27 = 'sudo-ubuntu:14.04'
  String basePy34 = 'sudo-python3:3.4.3-wheezy'

  // Base installs, including pycurl since it almost never installs right
  String installAptPybase = 'sudo apt-get install -y python-pip python-pycurl'
  String installAptPybasePy3 = 'sudo apt-get install -y python-pip'  // Should come with it, but just in case!
  String installYumPybase = 'sudo rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm && sudo yum install -y python-pip python-pycurl'

  // Libs needed to run pyresttest
  String install_libs = 'sudo pip install pyyaml'
  String install_libs_py3 = 'sudo pip install pycurl pyyaml future'
  String install_django_libs = 'sudo pip install "django==1.6.5" django-tastypie==0.12.1'

  // Tests
  String testBasic1 = "resttest.py --help | grep 'Usage' "
  String testBasic2 = "pyresttest --help | grep 'Usage' "
  String testImport = 'python -c "from pyresttest import validators"'  // Try importing
  String testApiDirect = "python pyresttest/resttest.py https://api.github.com examples/github_api_smoketest.yaml"
  String testApiUtil = "pyresttest https://api.github.com examples/github_api_smoketest.yaml"

  String pyr_install_pip_develop = 'sudo pip install -e .'

  def test_pip_develop_names = ['setup', 'install-pyresttest-pip-develop', 'test-cmdline1', 'test-cmdline2', 'import-test', 'functional-gh-test', 'test-functional-cmdline']

  def testPy26_pip_develop = [basePy26, [installYumPybase,    pyr_install_pip_develop, testBasic1, testBasic2, testApiDirect, testApiUtil]]
  def testPy27_pip_develop = [basePy27, [installAptPybase,    pyr_install_pip_develop, testBasic1, testBasic2, testApiDirect, testApiUtil]]
  def testPy34_pip_develop = [basePy34, [installAptPybasePy3, pyr_install_pip_develop, testBasic1, testBasic2, testApiDirect, testApiUtil]]

  docker.image('sudo-python3:3.4.3-wheezy').inside() {
    sh 'sudo rm -rf pyresttest'
  }
  dir('pyresttest') {
    git url:'https://github.com/svanoort/pyresttest.git', branch:pyresttestBranch
    stage 'Basic Test: pip develop mode install'
    execute_install_testset([testPy27_pip_develop, testPy26_pip_develop, testPy34_pip_develop], test_pip_develop_names)
  }
}

// Try installing from PyPi, run test files in the pyrestTest branch
void do_pypi_tests(String pyresttestBranch='master', String pypiServer='https://testpypi.python.org/pypi') {
   //Images with sudo, python and little else, for a bare installation
  String basePy26 = 'sudo-centos:6'
  String basePy27 = 'sudo-ubuntu:14.04'
  String basePy34 = 'sudo-python3:3.4.3-wheezy'

  // Base installs, including pycurl since it almost never installs right
  String installAptPybase = 'sudo apt-get install -y python-pip python-pycurl'
  String installAptPybasePy3 = 'sudo apt-get install -y python-pip'  // Should come with it, but just in case!
  String installYumPybase = 'sudo rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm && sudo yum install -y python-pip python-pycurl'

  // Tests
  String testBasic1 = "resttest.py --help | grep 'Usage' "
  String testBasic2 = "pyresttest --help | grep 'Usage' "
  String testImport = 'python -c "from pyresttest import validators"'  // Try importing
  String testApiDirect = "resttest.py https://api.github.com examples/github_api_smoketest.yaml"
  String testApiUtil = "pyresttest https://api.github.com examples/github_api_smoketest.yaml"

  String pyr_install_pypi = "sudo pip install -i $pypiServer pyresttest"

  def test_pypi_names = ['setup', 'install-from-pypi', 'test-cmdline1', 'test-cmdline2', 'import-test', 'functional-gh-test', 'test-functional-cmdline']

  def testPy26_pypi = [basePy26, [installYumPybase,    pyr_install_pypi, testBasic1, testBasic2, testApiDirect, testApiUtil]]
  def testPy27_pypi = [basePy27, [installAptPybase,    pyr_install_pypi, testBasic1, testBasic2, testApiDirect, testApiUtil]]
  def testPy34_pypi = [basePy34, [installAptPybasePy3, pyr_install_pypi, testBasic1, testBasic2, testApiDirect, testApiUtil]]

  docker.image('sudo-python3:3.4.3-wheezy').inside() {
    sh 'sudo rm -rf pyresttest-pypi'
  }
  dir('pyresttest-pypi') {
    git url:'https://github.com/svanoort/pyresttest.git', branch:pyresttestBranch
    sh 'rm -rf pyresttest'
    stage 'Basic Test: pip develop mode install'
    execute_install_testset([testPy27_pypi, testPy26_pypi, testPy34_pypi], test_pypi_names)
  }
}

// Run the main tests that don't require PyPI server
void do_main_tests(String pyresttestBranch='master') {
  do_clone_run(pyresttestBranch)
  do_directinstall_test(pyresttestBranch)
  do_pip_develop_tests(pyresttestBranch)
}


return this