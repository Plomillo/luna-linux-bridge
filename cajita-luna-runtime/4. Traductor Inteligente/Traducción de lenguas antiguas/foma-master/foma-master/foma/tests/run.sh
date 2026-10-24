#!/bin/sh
set -ex

FOMA=foma
if [ $# -gt 0 ]; then
  FOMA="$1"
fi

"$FOMA" -q -f test-leaky-redefine.foma || exit 1;
"$FOMA" -q -f test-segfault-eliminate.foma || exit 1;
if ! "$FOMA" -q -f test-error-rendering.foma  2>&1 | grep -q 'syntax error'
then
  exit 1
fi
"$FOMA" -q -f test-segfault-long-name > /dev/null || exit 1
"$FOMA" -q -f test-segfault-empty-fst.foma > /dev/null || exit 1;
"$FOMA" -q -f test-leaky-test.foma > /dev/null || exit 1;
