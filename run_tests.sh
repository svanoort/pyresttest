#!/usr/bin/bash
# Core pieces
echo stuff
python -m unittest pyresttest.test_parsing pyresttest.test_binding pyresttest.test_generators pyresttest.test_contenthandling pyresttest.test_validators

# Integrated components
python -m unittest pyresttest.test_resttest pyresttest.test_tests pyresttest.test_benchmarks

# Command-line call tests (use github API)
python pyresttest/functionaltest.py

# Extensions test
sh test_use_extension.sh

