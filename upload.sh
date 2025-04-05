#!/bin/bash

rm -rf dist/*

# build source distribution
python setup.py sdist

# build wheel with the correct platform tag
python setup.py bdist_wheel

# upload both source distribution and wheel
twine upload dist/*
