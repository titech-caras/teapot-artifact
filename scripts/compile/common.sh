#!/bin/bash

ROOTDIR=$(realpath "$(dirname "$0")"/../..)
ORIGINAL_BINARIES="$ROOTDIR"/binaries/original
SPECFUZZ_BINARIES="$ROOTDIR"/binaries/specfuzz

SF_CFLAGS="--enable-coverage -DNDEBUG -L/honggfuzz/libhfuzz -L/honggfuzz/libhfcommon -lhfuzz -lhfcommon"
export C_INCLUDE_PATH="$C_INCLUDE_PATH:$ROOTDIR/teapot-testcases"

NUM_THREADS=8