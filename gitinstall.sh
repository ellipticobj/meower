#!/bin/bash

# installer script
# this downloads a github release executable for the current arch and installs it
#
# repo details:
# https://github.com/REPO_OWNER/REPO_NAME should be the repository you want to download the executable from
# EXECUTABLE_NAME_HERE should be the name of the executable that the user will install

# credits: https://github.com/ellipticobj
# to user: USE WITH CAUTION! THIS SCRIPT CAN BE MODIFIED TO BE DANGEROUS. ALWAYS CHECK THE SCRIPT BEFORE RUNNING IT.

# ------------------------------------
# init variables
# ------------------------------------
REPO_OWNER="ellipticobj"
REPO_NAME="meower"
EXEC_NAME="meow"
SYSTEM_INSTALL_PATH="/usr/bin/"
USER_INSTALL_PATH="${HOME}/.local/bin/"

# ------------------------------------
# helpers
# ------------------------------------
error_exit() {
    echo -e "error: $1" >&2
    exit 1
}

# tells the user what this script does
echo "this script downloads the latest release of ${REPO_OWNER}/${REPO_NAME}"

echo "do you want to install?"
echo -n "enter to continue or any other key to exit "
read -r CONTINUE < /dev/tty
if [ -n "$CONTINUE" ]; then
    echo "exiting..."
    exit 0
fi

# ------------------------------------
# environment checks
# ------------------------------------
if [[ "$(uname)" != "Linux" && "$(uname)" != "Darwin" ]]; then
    echo "error: this script only supports linux and macos."
    exit 1
fi

for cmd in curl grep sed; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "error: $cmd is not installed."
        exit 1
    fi
done

# use jq if available
if command -v jq >/dev/null 2>&1; then
    USE_JQ=true
else
    USE_JQ=false
fi

# arch detection
ARCH=$(uname -m)
case "$ARCH" in
    x86_64)
        ARCH="x86_64"
        ;;
    aarch64)
        ARCH="aarch64"
        ;;
    arm64)
        ARCH="arm64"
        SYSTEM_INSTALL_PATH="/usr/local/bin/"
        ;;
  *)
    echo "unsupported architecture: $ARCH"
    exit 1
    ;;
esac

# ------------------------------------
# installation
# ------------------------------------
# gets latest release from GitHub API
API_URL="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/releases/latest"

# checks if jq is used
if [ "$USE_JQ" = true ]; then
    LATEST=$(curl -s "$API_URL" | jq -r '.tag_name')
else
    LATEST=$(curl -s "$API_URL" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
fi

if [ -z "$LATEST" ]; then
    echo "failed to fetch the latest release"
    echo "visit https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/latest to manually download the executable."
    exit 1
fi

# gets download url
# this assumes your release asset is named like this: EXEC_NAME-ARCH (e.g. meow-x86_64)
DOWNLOAD_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/download/${LATEST}/${EXEC_NAME}-${ARCH}"

# check if the file exists at the URL before downloading
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${DOWNLOAD_URL}")

echo "downloading executable from $DOWNLOAD_URL"
curl -L -o "${EXEC_NAME}" "$DOWNLOAD_URL" || error_exit "download failed"

FILESIZE=$(wc -c < "${EXEC_NAME}")
if [ "$FILESIZE" -lt 1048576 ]; then
    echo "error: downloaded file is ${FILESIZE} bytes (smaller than 1mb). the executable may not exist for your architecture."
    rm -f "${EXEC_NAME}"
    error_exit "executable not found on remote"
fi

# make file executable
chmod +x "$EXEC_NAME"

# ask where to install
echo -e "\nwhere would you like to install?"
echo "1) user only (${USER_INSTALL_PATH})"
echo "2) system-wide (${SYSTEM_INSTALL_PATH}, requires sudo)"
read -r -p "choose option [1-2, default=1]: " INSTALL_OPTION

INSTALL_OPTION=${INSTALL_OPTION:-1}

case $INSTALL_OPTION in
    1)
        mkdir -p "${USER_INSTALL_PATH}"
        
        # install to user directory
        cp "${EXEC_NAME}" "${USER_INSTALL_PATH}${EXEC_NAME}" || error_exit "failed to copy the executable"
        echo "installation complete: ${USER_INSTALL_PATH}${EXEC_NAME}"
        
        # check if directory is in PATH
        if [[ ":$PATH:" != *":${USER_INSTALL_PATH}:"* ]]; then
            echo "note: ${USER_INSTALL_PATH} is not in your PATH"
            echo "you may want to add it to your shell profile"
        fi
        ;;
    2)
        # install system-wide
        echo "installing to ${SYSTEM_INSTALL_PATH}${EXEC_NAME} (requires sudo)"
        sudo mv "${EXEC_NAME}" "${SYSTEM_INSTALL_PATH}${EXEC_NAME}" || error_exit "failed to move the executable."
        echo "installation complete: ${SYSTEM_INSTALL_PATH}${EXEC_NAME}"
        ;;
    *)
        echo "invalid option, exiting..."
        rm -f "${EXEC_NAME}"
        exit 1
        ;;
esac