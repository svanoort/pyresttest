from distutils.core import setup

setup(name='pyresttest',
    version='0.1',
    description='Python RESTful API Testing & Microbenchmarking Tool',
    long_description='Python RESTful API Testing & Microbenchmarking Tool',
    maintainer='Sam Van Oort',
    maintainer_email='acetonespam@gmail.com',
    url='https://github.com/svanoort/pyresttest',
    keywords='rest web http testing',
    py_modules=['pyresttest.resttest','pyresttest.generators','pyresttest.binding',
        'pyresttest.parsing', 'pyresttest.validators', 'pyresttest.contenthandling',
        'pyresttest.benchmarks','pyresttest.tests'],
    license='Apache License, Version 2.0',
    requires=['yaml','pycurl'],
    scripts=['pyresttest/resttest.py'], #Make this executable from command line when installed
    provides=['pyresttest']
)
