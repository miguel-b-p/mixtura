#!/usr/bin/env bash

# Move to the project root directory (parent of build/)
cd "$(dirname "$0")/.."

# Define paths (now relative to project root)
SOURCE_FILE="mixtura/main.py"
OUTPUT_DIR="bin"
VERSION_FILE="bin/VERSION"

# Read current version and increment minor version
CURRENT_VERSION=$(cat "$VERSION_FILE")
MAJOR=$(echo "$CURRENT_VERSION" | cut -d. -f1)
MINOR=$(echo "$CURRENT_VERSION" | cut -d. -f2)
NEW_MINOR=$((MINOR + 1))
NEW_VERSION="${MAJOR}.${NEW_MINOR}"

echo "Updating version: $CURRENT_VERSION -> $NEW_VERSION"

# Update VERSION files
echo "$NEW_VERSION" >"$VERSION_FILE"
echo "$NEW_VERSION" >"mixtura/VERSION"

# Update this script (build.sh)
sed -i "s/^FILE_VERSION=\".*\"/FILE_VERSION=\"$NEW_VERSION\"/" "$0"
sed -i "s/^PRODUCT_VERSION=\".*\"/PRODUCT_VERSION=\"$NEW_VERSION\"/" "$0"

# Update flake.nix
sed -i "s/version = \"[0-9]*\.[0-9]*\"/version = \"$NEW_VERSION\"/" "flake.nix"

# Update pyproject.toml
sed -i "s/^version = \"[0-9]*\.[0-9]*\"/version = \"$NEW_VERSION\"/" "pyproject.toml"

echo "Version updated successfully in all files!"

# Version/Metadata Information
COMPANY_NAME="Mixtura Project"
PRODUCT_NAME="Mixtura"
FILE_DESCRIPTION="Mixtura Package Manager"
COPYRIGHT_TEXT="Copyright (c) 2025 Mixtura Project"

echo "Building mixtura with Nuitka..."

python3 -m nuitka \
    --onefile \
    --follow-imports \
    --lto=yes \
    --company-name="$COMPANY_NAME" \
    --product-name="$PRODUCT_NAME" \
    --file-version="$NEW_VERSION" \
    --product-version="$NEW_VERSION" \
    --file-description="$FILE_DESCRIPTION" \
    --copyright="$COPYRIGHT_TEXT" \
    --output-dir="$OUTPUT_DIR" \
    --output-filename="mixtura" \
    --show-progress \
    --include-package=mixtura \
    --include-data-files=bin/VERSION=mixtura/VERSION \
    "$SOURCE_FILE"

echo "Build complete. Executable should be in $OUTPUT_DIR/mixtura"

# Generate Hash
echo "Generating hash..."
BINARY_PATH="$OUTPUT_DIR/mixtura"
HASH_FILE="$OUTPUT_DIR/HASH"

if [ -f "$BINARY_PATH" ]; then
    sha256sum "$BINARY_PATH" | awk '{print $1}' >"$HASH_FILE"
    echo "Hash saved to $HASH_FILE"
else
    echo "Error: Binary not found at $BINARY_PATH"
    exit 1
fi
