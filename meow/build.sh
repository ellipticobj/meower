#!/bin/bash

# cache directory
CACHE_DIR=".build_cache"
HASHES_FILE="${CACHE_DIR}/file_hashes.json"
mkdir -p "$CACHE_DIR"

# function to calculate hash of a single file
calchash_file() {
    sha256sum "$1" | cut -d' ' -f1
}

# function to load previous hashes
load_hashes() {
    if [ -f "$HASHES_FILE" ]; then
                python3 -c "
import json, sys, os

hashes_file = '$HASHES_FILE'
if os.path.exists(hashes_file):
    try:
        with open(hashes_file, 'r') as f:
            hashes = json.load(f)
            print(json.dumps(hashes))
    except json.JSONDecodeError:
        print('{}')
else:
    print('{}')
"
    else
        echo "{}"
    fi
}

# function to check if a file needs rebuilding
needs_rebuild() {
    local file="$1"
    local current_hash
    local stored_hashes
    local stored_hash
    
    current_hash=$(calchash_file "$file")
    stored_hashes=$(load_hashes)
    
    # extract hash using python3 to properly handle JSON
    stored_hash=$(python3 -c "
import json, sys

try:
    hashes = json.loads('$stored_hashes')
    print(hashes.get('$file', ''))
except:
    print('')
")
    
    if [ -z "$stored_hash" ] || [ "$stored_hash" != "$current_hash" ]; then
        echo "$current_hash"
        return 0  # true - needs rebuild
    else
        return 1  # false - no rebuild needed
    fi
}

# function to update hash for a file
update_hash() {
    local file="$1"
    local new_hash="${2:-}"
    
    # use provided hash or calculate it
    if [ -z "$new_hash" ]; then
        new_hash=$(calchash_file "$file")
    fi
    
    # use python3 to properly handle JSON
    python3 -c "
import json, sys, os

# load existing hashes
hashes_file = '$HASHES_FILE'
if os.path.exists(hashes_file):
    try:
        with open(hashes_file, 'r') as f:
            hashes = json.load(f)
    except json.JSONDecodeError:
        hashes = {}
else:
    hashes = {}

# update the hash for this file
hashes['$file'] = '$new_hash'

# save updated hashes
with open(hashes_file, 'w') as f:
    json.dump(hashes, f, indent=2)
"
}

# clean specific directories but preserve cache
selectiveclean() {
    rm -rf temp dist build *.so *.pyd
    mkdir -p temp
}

# detect architecture and set flags
ARCH=$(uname -m)
case "$ARCH" in
    x86_64)
        ARCH_FLAGS="-march=x86-64-v2 -mtune=generic"
        ;;
    aarch64|arm64)
        ARCH_FLAGS="-march=armv8-a+crc -mtune=generic"
        ;;
    *)
        ARCH_FLAGS="-mtune=generic"
        ;;
esac

# set compiler flags
CFLAGS="-O3 ${ARCH_FLAGS} -flto -fno-semantic-interposition -fomit-frame-pointer -pipe"
LDFLAGS="-O3 -flto -Wl,--as-needed -Wl,--gc-sections -Wl,--build-id=none"
export CFLAGS LDFLAGS

# determine number of CPU cores
CORES=$(python3 -c "import os; print(os.cpu_count())")
export MAKEFLAGS="-j$CORES"

# find all Cython source files
CYTHON_FILES=$(find . -type f \( -name "*.py" -o -name "*.pyx" -o -name "*.pxd" \) -not -path "./build/*" -not -path "./dist/*" -not -path "./${CACHE_DIR}/*")

# check each file and build if needed
CHANGED_FILES=()
CHANGED_HASHES=()

for file in $CYTHON_FILES; do
    CURRENT_HASH=$(needs_rebuild "$file")
    if [ $? -eq 0 ]; then
        echo "changes detected in $file, will rebuild this file..."
        CHANGED_FILES+=("$file")
        CHANGED_HASHES+=("$CURRENT_HASH")
    fi
done

if [ ${#CHANGED_FILES[@]} -gt 0 ]; then
    echo "building ${#CHANGED_FILES[@]} changed files..."
    
    # clean selectively
    selectiveclean

    # install dependencies (with pip cache)
    pip install -r ../requirements.txt -U || echo "no requirements.txt found"

    echo "building with $CORES cores on $ARCH architecture"

    # only rebuild modified files
    if [ ${#CHANGED_FILES[@]} -eq ${#CYTHON_FILES[@]} ]; then
        # if all files changed, just rebuild everything
        python3 local-setup.py build_ext \
            --build-lib=temp \
            --build-temp=temp/build_cython \
            --inplace \
            --force \
            --parallel=$CORES \
            --verbose
    else
        # build only changed files
        for file in "${CHANGED_FILES[@]}"; do
            echo "rebuilding: $file"
            python3 local-setup.py build_ext \
                --build-lib=temp \
                --build-temp=temp/build_cython \
                --inplace \
                --sources="$file" \
                --force \
                --verbose
        done
    fi

    # update hashes for changed files
    for i in "${!CHANGED_FILES[@]}"; do
        file="${CHANGED_FILES[$i]}"
        hash="${CHANGED_HASHES[$i]}"
        update_hash "$file" "$hash"
    done
else
    echo "No changes detected, using cached build"
fi

if grep -q '"-march=native",' local-setup.py; then
    sed -i 's/"-march=native",//' local-setup.py
    sed -i 's/"-mtune=native",//' local-setup.py
fi

echo "building executable..."
python3 -m PyInstaller \
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

# move and strip the executable
mv *.so ./temp/ 2>/dev/null || true
rm -rf *.spec

strip --strip-all -R .comment -R .note -R .gnu.version dist/meow
objcopy --strip-unneeded \
        --remove-section=.note* \
        --remove-section=.comment \
        --keep-symbols=python3.def \
        dist/meow

echo -e "\nExecutable size:"
du -sh dist/meow
file dist/meow

cp "dist/meow" "./dist/meow-${ARCH}"
echo "executable at: $(pwd)/dist/meow-${ARCH}"

# final hash update for any newly created files that weren't in the original list
echo "updating file hashes for next build..."
for file in $(find . -type f \( -name "*.py" -o -name "*.pyx" -o -name "*.pxd" \) -not -path "./build/*" -not -path "./dist/*" -not -path "./${CACHE_DIR}/*"); do
    if ! update_hash "$file"; then
        echo "warning: failed to update hash for $file"
    fi
done
echo "hashing done"

# installation prompt
echo -e "\ninstall to /usr/bin? [Y/n]"
read -r CONTINUE
if [[ "$CONTINUE" =~ ^[Nn]$ ]]; then
    echo "executable available at: $(pwd)/dist/meow-${ARCH}"
else
    sudo mv "dist/meow" "/usr/bin/meow"
    echo "installed to /usr/bin/meow"
    echo "uninstall with 'sudo rm -rf /usr/bin/meow'"
fi

# clean up temporary files
rm -rf __pycache__/ build/ temp/