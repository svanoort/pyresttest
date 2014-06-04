from distutils.core import setup

setup(name='pyresttest',
    version='0.1',
    description='Python Rest Testing',
    maintainer='Sam Van Oort',
    maintainer_email='acetonespam@gmail.com',
    url='https://github.com/svanoort/pyresttest',
    py_modules=['resttest','test_resttest'],
    license='Apache License, Version 2.0',
    requires=['argparse','yaml','pycurl']
    )
