#!/bin/bash -p
# Single build entry point: deterministic, hash-locked, unsigned, no installation.
DIR="$(cd -P -- "$(/usr/bin/dirname -- "$0")" && pwd)" || exit 1
if [ "$#" -eq 0 ]; then
    exec python3 -E -s "$DIR/tools/baseline.py" --help
fi
exec python3 -E -s "$DIR/tools/baseline.py" "$@"
