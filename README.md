pyresttest
==========

Python scripts for testing REST services.

# License
Apache License, Version 2.0

# Simple Test

Run a simple test that checks a URL returns a 200:

```
python resttest.py http://www.google.com simple_test.yaml
```

# Troubleshoot

## Cannot find argparse
```
sudo su -
easy_install argparse
exit
```
