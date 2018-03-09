import sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Future is needed for pip distribution for python 3 support
dependencies = ['pyyaml', 'pycurl']
test_dependencies = ['django==1.6.5','django-tastypie==0.12.1','jsonpath','jmespath']

# Add additional compatibility shims
if sys.version_info[0] > 2:
  dependencies.append('future')  # Only works with direct local installs, not via pip
else:
  test_dependencies.append('mock')
  test_dependencies.append('discover')

setup(name='pyresttest',
      version='1.7.2.dev',
      description='Python RESTful API Testing & Microbenchmarking Tool',
      long_description='Python RESTful API Testing & Microbenchmarking Tool \n Documentation at https://github.com/svanoort/pyresttest',
      author='Sam Van Oort',
      author_email='samvanoort@gmail.com',
      url='https://github.com/svanoort/pyresttest',
      keywords=['rest', 'web', 'http', 'testing'],
      classifiers=[
          'Environment :: Console',
          'License :: OSI Approved :: Apache Software License',
          'Natural Language :: English',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Topic :: Software Development :: Testing',
          'Topic :: Software Development :: Quality Assurance',
          'Topic :: Utilities'
      ],
      py_modules=['pyresttest.resttest', 'pyresttest.generators', 'pyresttest.binding',
                  'pyresttest.parsing', 'pyresttest.validators', 'pyresttest.contenthandling',
                  'pyresttest.benchmarks', 'pyresttest.tests',
                  'pyresttest.six','pyresttest.command_line',
                  'pyresttest.ext.validator_jsonschema',
                  'pyresttest.ext.extractor_jmespath'],
      license='Apache License, Version 2.0',
      install_requires=dependencies,
      tests_require=test_dependencies,
      extras_require= {
        'JSONSchema': ['jsonschema'],
        'JMESPath': ['jmespath']
      },
      # Make this executable from command line when installed
      entry_points = {
        'console_scripts': ['pyresttest=pyresttest.command_line:main'],
      },
      provides=['pyresttest']
      )
