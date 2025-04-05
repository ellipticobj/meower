#!/bin/bash


echo "building meower..."

# create cache directory
CACHE_DIR=".build_cache"
mkdir -p "$CACHE_DIR"

# clean previous build artifacts
rm -rf dist/ build/ *.spec temp/ *.so __pycache__/ meow/__pycache__/ meow/*/__pycache__/
mkdir -p dist temp

# install required dependencies
echo "installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# set architecture-specific flags for x86_64
ARCH_FLAGS="-march=x86-64-v2 -mtune=generic"

# set optimized compiler flags
CFLAGS="-O2 ${ARCH_FLAGS} -fPIC -pipe"
LDFLAGS="-Wl,--as-needed -Wl,--gc-sections"
export CFLAGS LDFLAGS

# determine number of CPU cores
CORES=$(python3 -c "import os; print(max(1, os.cpu_count() - 1))")
export MAKEFLAGS="-j$CORES"

echo "building with $CORES cores on x86_64 architecture"

# build the executable with PyInstaller
echo "building executable..."
python3 -m PyInstaller \
    -n meow \
    --clean \
    --strip \
    --optimize 2 \
    --onefile \
    main.py \
    --distpath=./dist \
    --log-level=INFO \
    --runtime-tmpdir=/tmp \
    --add-data="meow/config.py:meow" \
    --hidden-import=tqdm \
    --hidden-import=colorama \
    --hidden-import=gitpython \
    --hidden-import=argparse \
    --exclude-module=ssl \
    --exclude-module=lzma \
    --exclude-module=pytest \
    --exclude-module=curses \
    --exclude-module=sqlite3 \
    --exclude-module=tkinter \
    --exclude-module=unittest \
    --exclude-module=multiprocessing \
    --exclude-module=pyi_rth_inspect \
    --exclude-module=numpy \
    --exclude-module=pandas \
    --exclude-module=matplotlib \
    --exclude-module=scipy \
    --exclude-module=PIL \
    --exclude-module=PyQt5 \
    --exclude-module=PySide2 \
    --exclude-module=wx \
    --exclude-module=IPython \
    --exclude-module=notebook \
    --exclude-module=jupyter \
    --workpath=temp/build_pyinstaller

# strip the executable
echo "stripping executable..."
strip --strip-all dist/meow

# check executable size
echo -e "\nexecutable size:"
du -sh dist/meow
file dist/meow

# copy to architecture-specific name
mv "dist/meow" "./dist/meow-x86_64"
echo "executable at: $(pwd)/dist/meow-x86_64"

# installation prompt
echo -e "\ninstall to /usr/local/bin? [Y/n]"
read -r CONTINUE
if [[ "$CONTINUE" =~ ^[Nn]$ ]]; then
    echo "executable available at: $(pwd)/dist/meow-x86_64"
else
    sudo install -m 755 "dist/meow-x86_64" "/usr/local/bin/meow"
    echo "installed to /usr/local/bin/meow"
    echo "uninstall with 'sudo rm -f /usr/local/bin/meow'"
fi

echo "build completed successfully!"
