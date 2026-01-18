#!/usr/bin/env bash

set -e

# Configuration
INSTALL_DIR="$HOME/.local/bin"
BINARY_URL="https://github.com/miguel-b-p/mixtura/raw/refs/heads/master/bin/mixtura"
BINARY_NAME="mixtura"
TARGET_PATH="$INSTALL_DIR/$BINARY_NAME"
# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}:: Installing Mixtura...${NC}"

# 1. Create install directory if it doesn't exist
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${BLUE}:: Creating directory $INSTALL_DIR...${NC}"
    mkdir -p "$INSTALL_DIR"
fi

# 2. Download the binary
echo -e "${BLUE}:: Downloading $BINARY_NAME from GitHub...${NC}"
if command -v curl >/dev/null 2>&1; then
    curl -L -o "$TARGET_PATH" "$BINARY_URL"
elif command -v wget >/dev/null 2>&1; then
    wget -O "$TARGET_PATH" "$BINARY_URL"
else
    echo -e "${RED}Error: Neither curl nor wget found. Please install one of them.${NC}"
    exit 1
fi

# 3. Make executable
echo -e "${BLUE}:: Making $BINARY_NAME executable...${NC}"
chmod +x "$TARGET_PATH"

echo -e "${GREEN}✔ Mixtura installed successfully to $TARGET_PATH${NC}"

# 3.1 Create 'mix' alias
MIX_SYMLINK="$INSTALL_DIR/mix"
echo -e "${BLUE}:: Creating 'mix' alias...${NC}"
ln -sf "$TARGET_PATH" "$MIX_SYMLINK"
echo -e "${GREEN}✔ Alias 'mix' created at $MIX_SYMLINK${NC}"

# 4. Check PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo -e "${YELLOW}⚠ Warning: $INSTALL_DIR is not in your PATH.${NC}"
    echo "Please add the following line to your shell configuration file (.bashrc, .zshrc, etc.):"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
fi
