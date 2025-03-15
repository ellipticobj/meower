#!/bin/bash
set -euo pipefail

rm -rf temp dist build *.so *.pyd
mkdir -p temp

export CFLAGS="-O3 -march=native -flto -fno-semantic-interposition -fomit-frame-pointer"
export LDFLAGS="-O3 -flto -Wl,--as-needed"
export CORES=$(python -c "import os; print(os.cpu_count())")
export SETUPTOOLS_USE_DISTUTILS=stdlib
export MAKEFLAGS="-j$CORES"

pip install --no-cache-dir -r ../requirements.txt || echo "no requirements.txt found"
pip install --no-cache-dir --upgrade cython setuptools

python local-setup.py build_ext \
    --build-lib=temp \
    --build-temp=temp/build_cython \
    --inplace \
    --force \
    --parallel=$CORES \
    --verbose

python -m PyInstaller \
    -n meow \
    --clean \
    --strip \
    -d noarchive \
    --optimize 2 \
    --onefile main.py \
    --distpath=./dist \
    --log-level=ERROR \
    --runtime-tmpdir=. \
    --add-data="config.py:." \
    --hidden-import=tqdm \
    --hidden-import=helpers \
    --hidden-import=loaders \
    --hidden-import=loggers \
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
    --workpath=temp/build_pyinstaller \

mv *.so ./temp/
rm -rf *.spec

strip --strip-all -R .comment -R .note -R .gnu.version dist/meow
objcopy --strip-unneeded \
        --remove-section=.note* \
        --remove-section=.comment \
        --keep-symbols=python.def \
        dist/meow

echo -e "\nfinal executable size:"
du -sh dist/meow
file dist/meow

echo -e "\ninstall to /usr/local/bin? [Y/n]"
read -r CONTINUE
if [[ "$CONTINUE" =~ ^[Nn]$ ]]; then
    echo "executable available at: $(pwd)/dist/meow"
else
    sudo mv "dist/meow" "/usr/bin/meow"
    echo "installed to /usr/bin/meow"
fi

echo "uninstall with 'sudo rm -rf /usr/bin/meow'"

rm -rf __pycache__/ build/ temp/
