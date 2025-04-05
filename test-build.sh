#!/bin/bash

# Test build script for x86_64 Linux systems
set -e

echo "Building test executable for x86_64 Linux..."

# Clean previous build artifacts
rm -rf dist/ build/ *.spec temp/ *.so __pycache__/
mkdir -p dist temp

# Install required dependencies
echo "Installing dependencies..."
pip install colorama pyinstaller

# Build the test executable with PyInstaller
echo "Building test executable..."
python3 -m PyInstaller \
    -n meow-test \
    --clean \
    --strip \
    --optimize 2 \
    --onefile \
    test-main.py \
    --distpath=./dist \
    --log-level=INFO \
    --hidden-import=colorama \
    --exclude-module=ssl \
    --exclude-module=lzma \
    --exclude-module=pytest \
    --exclude-module=curses \
    --exclude-module=sqlite3 \
    --exclude-module=tkinter \
    --exclude-module=unittest \
    --exclude-module=multiprocessing \
    --workpath=temp/build_pyinstaller

# Strip the executable
echo "Stripping executable..."
strip --strip-all dist/meow-test

# Check executable size
echo -e "\nExecutable size:"
du -sh dist/meow-test
file dist/meow-test

echo "Test build completed. Run with: ./dist/meow-test"
