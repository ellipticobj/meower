#!/bin/bash
set -euo pipefail

# Detect OS for platform-specific flags
OS=$(uname)
if [[ "$OS" == "Linux" ]]; then
    COMPILER_FLAGS="-Oz -flto=4 -fno-ident"
    LINKER_FLAGS="-Wl,--gc-sections -Wl,--build-id=none"
elif [[ "$OS" == "Darwin" ]]; then
    COMPILER_FLAGS="-Oz -flto"
    LINKER_FLAGS="-Wl,-dead_strip"
else
    echo "Unsupported OS: $OS"
    exit 1
fi

# Detect architecture
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

echo "Installing dependencies..."
pip install --upgrade pip setuptools wheel cython
pip install -r requirements.txt --upgrade

echo "Building and installing meow..."
CFLAGS="${COMPILER_FLAGS} ${ARCH_FLAGS}" \
LDFLAGS="${LINKER_FLAGS}" \
pip install --force-reinstall --no-cache-dir --compile \
    --user -e . \
    --global-option="build_ext" \
    --global-option="--inplace"

# Create installation directory if it doesn't exist
INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "$INSTALL_DIR"

# Create symlink to executable for convenience
if [[ -z "$(which meow)" ]]; then
    echo "Creating symlink to executable..."
    ln -sf "$(pwd)/meow/__main__.py" "${INSTALL_DIR}/meow"
    chmod +x "${INSTALL_DIR}/meow"
    echo "Added meow to ${INSTALL_DIR}. Make sure this directory is in your PATH."
fi

echo -e "\nInstallation successful!"
echo -e "Run with 'meow'"
echo -e "For a production build, run: cd meow && ./build.sh"