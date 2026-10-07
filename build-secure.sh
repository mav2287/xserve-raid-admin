#!/bin/bash -p
# audit28 intermediate only; architecture-specific packaging is a separate step.
DIR="$(cd -P -- "$(/usr/bin/dirname -- "$0")" && pwd)" || exit 1
if [ "$#" -eq 0 ]; then exec python3 -E -s "$DIR/tools/secure_build.py" --help; fi
exec python3 -E -s "$DIR/tools/secure_build.py" "$@"
