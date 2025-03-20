#!/bin/bash

# clean up previous builds
rm -rf temp dist build *.so *.pyd
mkdir -p temp

ARCH=$(uname -m)
case "$ARCH" in
    x86_64)
        # generic x86-64 flags
        ARCH_FLAGS="-march=x86-64-v2 -mtune=generic"
        ;;
    aarch64|arm64)
        # ARM64 optimizations
        ARCH_FLAGS="-march=armv8-a+crc -mtune=generic"
        ;;
    *)
        # default case for other architectures
        ARCH_FLAGS="-mtune=generic"
        ;;
esac

# set compiler flags for speed
export CFLAGS="-O3 ${ARCH_FLAGS} -flto -fno-semantic-interposition -fomit-frame-pointer -pipe"
export LDFLAGS="-O3 -flto -Wl,--as-needed -Wl,--gc-sections -Wl,--build-id=none"
export CORES=$(python -c "import os; print(os.cpu_count())")
export MAKEFLAGS="-j$CORES"

# install dependencies
pip install -r ../requirements.txt -U --no-cache-dir || echo "no requirements.txt found"

echo "Building with $CORES cores on $ARCH architecture"

# build cython modules
python local-setup.py build_ext \
    --build-lib=temp \
    --build-temp=temp/build_cython \
    --inplace \
    --force \
    --parallel=$CORES \
    --verbose

# modify local-setup.py to remove "native" architecture flags for portability
sed -i 's/"-march=native",//' local-setup.py
sed -i 's/"-mtune=native",//' local-setup.py

# build executable
python -m PyInstaller \
    -n meow \
    --clean \
    --strip \
    -d noarchive \
    --optimize 2 \
    --onefile \
    --noupx \
    main.py \
    --distpath=./dist \
    --log-level=ERROR \
    --runtime-tmpdir=. \
    --add-data="config.py:meow" \
    --hidden-import=tqdm \
    --hidden-import=meow.utils.helpers \
    --hidden-import=meow.utils.loaders \
    --hidden-import=meow.utils.loggers \
    --hidden-import=meow.utils.gitutils \
    --hidden-import=inspect \
    --hidden-import=colorama \
    --hidden-import=encodings \
    --exclude-module ssl \
    --exclude-module lzma \
    --exclude-module pytest \
    --exclude-module curses \
    --exclude-module sqlite3 \
    --exclude-module tkinter \
    --exclude-module unittest \
    --exclude-module multiprocessing \
    --exclude-module=pyi_rth_inspect \
    --workpath=temp/build_pyinstaller

mv *.so ./temp/ 2>/dev/null || true
rm -rf *.spec

strip --strip-all -R .comment -R .note -R .gnu.version dist/meow
objcopy --strip-unneeded \
        --remove-section=.note* \
        --remove-section=.comment \
        --keep-symbols=python.def \
        dist/meow

echo -e "\n executable size:"
du -sh dist/meow
file dist/meow

cp "dist/meow" "./dist/meow-${ARCH}"
echo "executable at: $(pwd)/dist/meow-${ARCH}"

echo -e "\nInstall to /usr/local/bin? [Y/n]"
read -r CONTINUE
if [[ "$CONTINUE" =~ ^[Nn]$ ]]; then
    echo "Executable available at: $(pwd)/dist/meow-${ARCH}"
else
    sudo mv "dist/meow" "/usr/local/bin/meow"
    echo "Installed to /usr/local/bin/meow"
    echo "Uninstall with 'sudo rm -rf /usr/local/bin/meow'"
fi

rm -rf __pycache__/ build/ temp/