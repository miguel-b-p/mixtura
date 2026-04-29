#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
cp VERSION ../bin/VERSION
go build -trimpath -ldflags="-s -w" -o ../bin/mixtura .
sha256sum ../bin/mixtura | awk '{print $1}' > ../bin/HASH
