#!/bin/bash

# installer script
# this downloads a github release executable for the current arch and installs it to the /usr/bin/ directory
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
INSTALL_PATH="/usr/bin/"

# ------------------------------------
# helpers
# ------------------------------------
error_exit() {
    echo -e "error: $1" >&2
    exit 1
}

# tells the user what this script does
echo "this script downloads the latest release of ${REPO_OWNER}/${REPO_NAME} and installs it to ${INSTALL_PATH}"

echo "note: you may be prompted to input your password. this is to move the executable to ${INSTALL_PATH}"
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
    aarch64|arm64)
        ARCH="aarch64"
        ;;
  *)
    echo "Unsupported architecture: $ARCH"
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
# this assumes your release asset is named like this: EXEC_NAME-ARCH (e.g. meows-x86_64)
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

# installs the file
chmod +x "$EXEC_NAME"
echo "moving executable to ${INSTALL_PATH}${EXEC_NAME}"
INSTALL_SOURCE="${EXEC_NAME}"

sudo mv "${INSTALL_SOURCE}" "${INSTALL_PATH}${EXEC_NAME}" || error_exit "failed to move the executable."
echo "installation complete: ${INSTALL_PATH}${EXEC_NAME}"