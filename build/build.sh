#!/usr/bin/env bash

# Ensure we are in the build directory
cd "$(dirname "$0")"

# Define paths
SOURCE_FILE="../src/main.py"
OUTPUT_DIR="../bin"
CONFIG_FILE="nuitka-config.yaml"

# Version/Metadata Information
COMPANY_NAME="Mixtura Project"
PRODUCT_NAME="Mixtura"
FILE_VERSION="1.0.0.0"
PRODUCT_VERSION="1.0.0.0"
FILE_DESCRIPTION="Mixtura Package Manager"
COPYRIGHT_TEXT="Copyright (c) 2025 Mixtura Project"

echo "Building mixtura with Nuitka..."

python3 -m nuitka \
    --onefile \
    --follow-imports \
    --lto=yes \
    --company-name="$COMPANY_NAME" \
    --product-name="$PRODUCT_NAME" \
    --file-version="$FILE_VERSION" \
    --product-version="$PRODUCT_VERSION" \
    --file-description="$FILE_DESCRIPTION" \
    --copyright="$COPYRIGHT_TEXT" \
    --output-dir="$OUTPUT_DIR" \
    --user-package-configuration-file="$CONFIG_FILE" \
    --output-filename="mixtura" \
    --remove-output \
    --show-progress \
    --include-package=modules \
    "$SOURCE_FILE"

echo "Build complete. Executable should be in $OUTPUT_DIR/mixtura"
