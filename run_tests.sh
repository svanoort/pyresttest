#!/usr/bin/bash
# Core pieces

# Python before 2.7

python -c 'import sys; exit(sys.version_info[0:2] < (2,7))'  # Return exit code 1 if before python 2.7
if [ $? -ne 0 ]; then  # Module discover pip-installed for test discovery
    python -m discover -s pyresttest -p 'test_*.py'
else
    python -m unittest discover -s pyresttest -p 'test_*.py'
fi



if [ $? -ne 0 ]; then
    exit 1
fi

# Command-line call tests (use github API)
python pyresttest/functionaltest.py

if [ $? -ne 0 ]; then
    exit 1
fi

# Extensions test
sh test_use_extension.sh

if [ $? -ne 0 ]; then
    exit 1
fi

