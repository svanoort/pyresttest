from distutils.core import setup

setup(name='pyresttest',
    version='0.1',
    description='Python RESTful API Testing & Microbenchmarking Tool',
    maintainer='Sam Van Oort',
    maintainer_email='acetonespam@gmail.com',
    url='https://github.com/svanoort/pyresttest',
    keywords='rest web http testing',
    packages=['pyresttest'],
    license='Apache License, Version 2.0',
    requires=['argparse','yaml','pycurl']
)
