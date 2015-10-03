#!/usr/bin/bash
# Core pieces
python -m unittest discover -s pyresttest -p 'test_*.py'

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

