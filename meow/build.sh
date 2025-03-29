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
        cat "$HASHES_FILE"
    else
        echo "{}"
    fi
}

# function to save new hashes
save_hashes() {
    echo "$1" > "$HASHES_FILE"
}

# function to check if a file needs rebuilding
needs_rebuild() {
    local file="$1"
    local current_hash
    local stored_hashes
    local stored_hash
    
    current_hash=$(calchash_file "$file")
    stored_hashes=$(load_hashes)
    
    # extract hash for this file from stored_hashes JSON
    stored_hash=$(echo "$stored_hashes" | grep -o "\"$file\": \"[^\"]*\"" | cut -d'"' -f4)
    
    # return 0 (true) if hashes differ or stored hash doesn't exist
    [ -z "$stored_hash" ] || [ "$stored_hash" != "$current_hash" ]
}

# function to update hash for a file
update_hash() {
    local file="$1"
    local new_hash
    local stored_hashes
    
    new_hash=$(calchash_file "$file")
    stored_hashes=$(load_hashes)
    
    # update hash in JSON
    if [ "$(echo "$stored_hashes" | grep -c .)" -eq 0 ]; then
        # empty JSON
        stored_hashes="{\"$file\": \"$new_hash\"}"
    else
        # remove closing brace, add new entry
        stored_hashes=$(echo "$stored_hashes" | sed 's/}$//')
        if [ "$(echo "$stored_hashes" | grep -c ':')" -gt 0 ]; then
            stored_hashes="$stored_hashes,\"$file\": \"$new_hash\"}"
        else
            stored_hashes="$stored_hashes\"$file\": \"$new_hash\"}"
        fi
    fi
    
    save_hashes "$stored_hashes"
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
CORES=$(python -c "import os; print(os.cpu_count())")
export MAKEFLAGS="-j$CORES"

# find all Cython source files
CYTHON_FILES=$(find . -type f \( -name "*.py" -o -name "*.pyx" -o -name "*.pxd" \) -not -path "./build/*" -not -path "./dist/*" -not -path "./${CACHE_DIR}/*")

# check each file and build if needed
REBUILD_NEEDED=0
for file in $CYTHON_FILES; do
    if needs_rebuild "$file"; then
        echo "Changes detected in $file, will rebuild..."
        REBUILD_NEEDED=1
        break
    fi
done

if [ $REBUILD_NEEDED -eq 1 ]; then
    echo "Building changed files..."
    
    # clean selectively
    selectiveclean

    # install dependencies (with pip cache)
    pip install -r ../requirements.txt -U || echo "no requirements.txt found"

    echo "building with $CORES cores on $ARCH architecture"

    # build cython modules
    python local-setup.py build_ext \
        --build-lib=temp \
        --build-temp=temp/build_cython \
        --inplace \
        --force \
        --parallel=$CORES \
        --verbose

    # update hashes for all files
    for file in $CYTHON_FILES; do
        update_hash "$file"
    done
else
    echo "No changes detected, using cached build"
fi

# modify local-setup.py for portability (only if it hasn't been modified)
if grep -q '"-march=native",' local-setup.py; then
    sed -i 's/"-march=native",//' local-setup.py
    sed -i 's/"-mtune=native",//' local-setup.py
fi

# build executable (always do this part as it's relatively quick)
echo "Building executable..."
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

# move and strip the executable
mv *.so ./temp/ 2>/dev/null || true
rm -rf *.spec

strip --strip-all -R .comment -R .note -R .gnu.version dist/meow
objcopy --strip-unneeded \
        --remove-section=.note* \
        --remove-section=.comment \
        --keep-symbols=python.def \
        dist/meow

echo -e "\nExecutable size:"
du -sh dist/meow
file dist/meow

cp "dist/meow" "./dist/meow-${ARCH}"
echo "Executable at: $(pwd)/dist/meow-${ARCH}"

# installation prompt
echo -e "\nInstall to /usr/bin? [Y/n]"
read -r CONTINUE
if [[ "$CONTINUE" =~ ^[Nn]$ ]]; then
    echo "Executable available at: $(pwd)/dist/meow-${ARCH}"
else
    sudo mv "dist/meow" "/usr/bin/meow"
    echo "Installed to /usr/bin/meow"
    echo "Uninstall with 'sudo rm -rf /usr/bin/meow'"
fi

# clean up temporary files
rm -rf __pycache__/ build/ temp/
