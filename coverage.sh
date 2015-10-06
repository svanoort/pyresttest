#!/bin/bash
# pip install coverage
coverage run --pylib --source pyresttest --branch -m unittest discover -s pyresttest -p 'test_*.py'
coverage html

# coverage run --pylib --branch pyresttest/functionaltest.py
# coverage html