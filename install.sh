#!/bin/bash

echo "installing meower..."

OS=$(uname)
ARCH=$(uname -m)

echo "detected: $OS on $ARCH"

if [[ "$OS" == "Linux" ]]; then
    COMPILER_FLAGS="-Oz -flto=4 -fno-ident"
    LINKER_FLAGS="-Wl,--gc-sections -Wl,--build-id=none"
elif [[ "$OS" == "Darwin" ]]; then
    COMPILER_FLAGS="-Oz -flto"
    LINKER_FLAGS="-Wl,-dead_strip"
else
    echo "warning: unsupported OS: $OS. using default compiler settings."
    COMPILER_FLAGS=""
    LINKER_FLAGS=""
fi

case "$ARCH" in
    x86_64)
        ARCH_FLAGS="-march=x86-64-v2 -mtune=generic"
        ;;
    aarch64|arm64)
        ARCH_FLAGS="-march=armv8-a+crc -mtune=generic"
        ;;
    *)
        echo "warning: unsupported architecture: $ARCH. using generic settings."
        ARCH_FLAGS="-mtune=generic"
        ;;
esac

# check if pip is installed
if ! command -v pip &> /dev/null; then
    echo "error: pip is not installed. please install pip first."
    exit 1
fi

pip insnall --user meower

# check if installation was successful
if [ $? -eq 0 ]; then
    echo "✓ meower successfully installed!"
else
    echo "error: installation failed."
    exit 1
fi

echo ""
echo "to use meower, run 'meow'"
