from distutils.core import setup

setup(name='pyresttest',
      version='1.6.1.dev',
      description='Python RESTful API Testing & Microbenchmarking Tool',
      long_description='Python RESTful API Testing & Microbenchmarking Tool \n Documentation at https://github.com/svanoort/pyresttest',
      maintainer='Sam Van Oort',
      maintainer_email='samvanoort@gmail.com',
      url='https://github.com/svanoort/pyresttest',
      keywords=['rest', 'web', 'http', 'testing'],
      classifiers=[
          'Environment :: Console',
          'License :: OSI Approved :: Apache Software License',
          'Natural Language :: English',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Software Development :: Testing',
          'Topic :: Software Development :: Quality Assurance',
          'Topic :: Utilities'
      ],
      py_modules=['pyresttest.resttest', 'pyresttest.generators', 'pyresttest.binding',
                  'pyresttest.parsing', 'pyresttest.validators', 'pyresttest.contenthandling',
                  'pyresttest.benchmarks', 'pyresttest.tests', 'pyresttest.ext.validator_jsonschema'],
      license='Apache License, Version 2.0',
      install_requires=['pyyaml', 'pycurl'],
      # Make this executable from command line when installed
      scripts=['util/pyresttest', 'util/resttest.py'],
      provides=['pyresttest']
      )
