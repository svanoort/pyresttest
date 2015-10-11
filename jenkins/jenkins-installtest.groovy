def testEnv = docker.image('pyresttest-build-ubuntu-14:latest')
def testEnv26 = docker.image('pyresttest-build-centos6:latest')
def centos = docker.image('centos:centos6')
def ubuntu = docker.image('ubuntu:14.04')
def args = '-u root'  //We need this to allow installs inside container

def headlesstests() {
    // Tests that only require python/pip and a pyresttest installation, no django server
    echo 'Running headless test'

    // The dir command causes a hangup *sigh*
    //dir('/tmp') {
    //    sh 'python -c "import pyresttest"'
        // Check command will run, but capture error code since help will also return error code
        sh "resttest.py 2>/dev/null | grep 'Usage' "
        sh "pyresttest 2>/dev/null | grep 'Usage' "
//    }
    sh "resttest.py https://api.github.com github_api_smoketest.yaml" // Real test
}


// Really finnicky, gets connection refused for reasons I cannot discern sometimes (docker issues?)
def servertests() {
    // Tests that require a full test server running to execute
    //dir ('/tmp') {
        echo 'Skipping server test'
//        sh "python pyresttest/testapp/manage.py testserver pyresttest/testapp/test_data.json &"
//        sh "pyresttest http://localhost:8000 pyresttest/content-test.yaml"
    //}
}

def clean_workspace() {
    sh 'rm -rf /tmp/work'
    def cur = pwd()
    sh "cp -rf $cur /tmp/work"
    sh 'cd /tmp/work'
}

node {
    git url:'https://github.com/svanoort/pyresttest.git', branch:'jenkins-installtest'

    //sh 'git clean -fdx' //Hangs it!

    // Test easyinstall, etc installation of scripts
    testEnv.inside(args) {
        clean_workspace()
        sh 'python setup.py install'
        headlesstests()
        servertests()
    }

    // Test standard local build/install with CentOS 6 / python 2.6
    testEnv26.inside(args) {
        clean_workspace()
        sh 'python setup.py install'
        headlesstests()
        servertests()
    }

     // Test RPM build/install
    testEnv26.inside(args) {
        clean_workspace()
        sh 'python setup.py bdist_rpm'
        stash includes: 'dist/*.noarch.rpm', name: 'rpm-py26'
        sh 'rpm -if dist/*.noarch.rpm'
        headlesstests()
        servertests()
    }

    // THIS DOESN'T WORK YET, SIGH
    /*stage name:'Publish to test PyPi', concurrency:1
    withCredentials([[$class: 'FileBinding', variable: 'SECRET', credentialsId: '014760b9-3146-49e6-8198-849094a28246']]) {
        sh 'cp $SECRET .pypirc'
    }
    testEnv.inside(args) {
        'cp .pypirc ~/.pypirc'
        clean_workspace()
        // Requires credentials and credentials binding plugin
        // Uses a secret stored pypirc file with pypitest enabled
        sh 'python setup.py sdist bdist upload -r pypitest'
        //TODO Needs some setup to enable wheel packaging
    }
    */

    stage name:'Test PyPy installation'

    // Smoketest pip installation in a naked CentOS image
    centos.inside(args) {
        clean_workspace()
        sh 'rpm -ivh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm'
        sh 'yum install -y python-pip'
        sh 'pip install -i https://testpypi.python.org/pypi pyresttest'
        headlesstests()
    }

    // Smoketest RPM installation in a naked CentOS image
    centos.inside(args) {
        clean_workspace()
        dir ("/tmp") {
            unstash name: 'rpm-py26'
            sh 'rpm -if dist/*.noarch.rpm'
            sh 'yum install -y PyYAML'
        }
        headlesstests()
    }

    // Smoketest pip installation inside a naked ubuntu 14 image
    ubuntu.inside(args) {
        clean_workspace()
        sh 'apt-get update && apt-get install -y python-pip'
        sh 'pip install -i https://testpypi.python.org/pypi pyresttest'
        headlesstests()
    }

    // Functional test using integrated server
    testEnv.inside(args) {
        clean_workspace()
        sh 'pip install -i https://testpypi.python.org/pypi pyresttest'
        servertests()
    }

    // Functional test using integrated server
    testEnv26.inside(args) {
        clean_workspace()
        sh 'pip install -i https://testpypi.python.org/pypi pyresttest'
        servertests()
    }
}