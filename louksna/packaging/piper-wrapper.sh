#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
export PYTHONNOUSERSITE=1
exec "$HERE/python/bin/python3" -m piper "$@"
