def run_test(dockerImg, python_name, version) {
  def id = dockerImg.id
  echo "My id is $id"
  try {
    dockerImg.inside {
      sh "$python_name /tmp/verify_image.py"
    }
    dockerImg.tag(version, true)
    dockerImg.tag('latest', true)
  } catch (Exception e) {
    error('BUILD FAILED FOR IMAGENAME '+id)
  } finally {
    sh "docker rmi $id"
  }
}

node {
  git url:'https://github.com/svanoort/pyresttest.git', branch:'feature-docker-and-ci-fixes'

  stage name:'build', concurrency: 1
  def ubuntu14_py27 = docker.build("pyresttest-build-ubuntu-14:test", 'docker/ubuntu14-py27')
  def centos6_py26 = docker.build("pyresttest-build-centos6:test", 'docker/centos6-py26')
  def python3 = docker.build("pyresttest-build-python3:test", 'docker/python3')

  stage name:'test/tag', concurrency: 1
  run_test(ubuntu14_py27, 'python', '0.1')
  run_test(centos6_py26, 'python', '0.1')
  run_test(python3, 'python3', '0.2')
}

